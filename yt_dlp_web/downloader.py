from __future__ import annotations

import logging
import os
import random
import re
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

try:
    import yt_dlp  # type: ignore[import-untyped]
except ImportError:
    yt_dlp = None

logger = logging.getLogger(__name__)

# Realistic user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class ErrorType(Enum):
    """Classification of download errors"""

    NOT_FOUND = "not_found"  # 404 - video deleted/private
    FORBIDDEN = "forbidden"  # 403 - access denied
    GEO_BLOCKED = "geo_blocked"  # Geographic restriction
    AGE_RESTRICTED = "age_restricted"  # Requires login/age verification
    COPYRIGHT = "copyright"  # DMCA/copyright takedown
    NETWORK_ERROR = "network_error"  # Timeout/connection issues
    RATE_LIMITED = "rate_limited"  # Too many requests
    EXTRACTION_ERROR = "extraction"  # Can't parse video data
    UNKNOWN = "unknown"  # Other errors


class DownloadStatus:
    def __init__(self, job_id: str, url: str):
        self.job_id = job_id
        self.url = url
        self.status = "queued"  # queued, downloading, completed, failed, skipped
        self.progress = 0
        self.filename: Optional[str] = None
        self.error: Optional[str] = None
        self.error_type: Optional[ErrorType] = None
        self.error_suggestion: Optional[str] = None
        self.is_retryable = False
        self.retry_count = 0
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.speed: Optional[float] = None
        self.eta: Optional[int] = None
        self.downloaded_bytes: Optional[int] = None
        self.total_bytes: Optional[int] = None


class YTDLPDownloader:
    def __init__(
        self,
        download_dir: str,
        rate_limit_seconds: float = 3.0,
        sleep_interval: tuple[float, float] = (1.0, 3.0),
        cookies_file: Optional[str] = None,
        allow_duplicates: bool = False,
        overwrite_existing: bool = False,
        use_download_archive: bool = True,
        max_concurrent_downloads: int = 3,
    ):
        self.download_dir = download_dir
        self.jobs: Dict[str, DownloadStatus] = {}
        self.rate_limit_seconds = rate_limit_seconds
        self.sleep_interval = sleep_interval
        self.cookies_file = cookies_file
        self.allow_duplicates = allow_duplicates
        self.overwrite_existing = overwrite_existing
        self.use_download_archive = use_download_archive
        self.last_download_time = 0.0
        self.download_lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_downloads)

        # Download archive file to track completed downloads
        self.archive_file = os.path.join(download_dir, ".yt-dlp-archive.txt")
        if use_download_archive:
            # Ensure archive file directory exists
            os.makedirs(os.path.dirname(self.archive_file), exist_ok=True)
            logger.info(f"Using download archive: {self.archive_file}")

    def normalize_url(self, url: str) -> str:
        """Normalize URL for duplicate detection"""
        try:
            parsed = urlparse(url.lower().strip())
            # Remove www prefix
            netloc = parsed.netloc.replace("www.", "")
            # Sort query parameters
            query_params = parse_qs(parsed.query)
            sorted_query = urlencode(sorted(query_params.items()), doseq=True)
            # Reconstruct normalized URL
            normalized = urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path.rstrip("/"),
                    parsed.params,
                    sorted_query,
                    "",  # Remove fragment
                )
            )
            return normalized
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return url.lower().strip()

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
        # Remove multiple consecutive dashes and spaces
        filename = re.sub(r"[-\s]+", "-", filename)
        # Remove leading/trailing dashes and spaces
        filename = filename.strip("- ")
        return filename

    def classify_error(self, error_msg: str) -> tuple[ErrorType, str, bool]:
        """Classify error and provide user-friendly message with retry hint"""
        error_lower = error_msg.lower()

        # 404 / Not Found
        if (
            "404" in error_lower
            or "not found" in error_lower
            or "video unavailable" in error_lower
            or "video not available" in error_lower
            or "has been removed" in error_lower
            or "this video is unavailable" in error_lower
        ):
            return (
                ErrorType.NOT_FOUND,
                "Video not found or has been removed/deleted. Check if the URL is correct.",
                False,
            )

        # 403 / Forbidden
        if "403" in error_lower or "forbidden" in error_lower:
            return (
                ErrorType.FORBIDDEN,
                "Access forbidden. The video may be private or require authentication.",
                False,
            )

        # Geo-blocking
        if (
            "geo" in error_lower
            or "not available in your country" in error_lower
            or "location" in error_lower
        ):
            return (
                ErrorType.GEO_BLOCKED,
                "Video is geo-blocked in your region. Try using a VPN or proxy.",
                False,
            )

        # Age restricted
        if "age" in error_lower or "sign in to confirm" in error_lower or "login" in error_lower:
            return (
                ErrorType.AGE_RESTRICTED,
                "Video is age-restricted. Provide cookies file from authenticated browser session.",
                False,
            )

        # Copyright
        if "copyright" in error_lower or "dmca" in error_lower or "removed" in error_lower:
            return (ErrorType.COPYRIGHT, "Video removed due to copyright claim.", False)

        # Rate limiting
        if (
            "rate" in error_lower
            or "too many" in error_lower
            or "429" in error_lower
            or "slow down" in error_lower
        ):
            return (
                ErrorType.RATE_LIMITED,
                "Rate limited by server. Increase RATE_LIMIT_SECONDS and try again later.",
                True,
            )

        # Network errors
        if (
            "timeout" in error_lower
            or "connection" in error_lower
            or "network" in error_lower
            or "unreachable" in error_lower
        ):
            return (
                ErrorType.NETWORK_ERROR,
                "Network error. Check your internet connection and try again.",
                True,
            )

        # Extraction errors
        if "extract" in error_lower or "parse" in error_lower or "unsupported" in error_lower:
            return (
                ErrorType.EXTRACTION_ERROR,
                "Failed to extract video information. The site format may have changed.",
                False,
            )

        # Unknown
        return (ErrorType.UNKNOWN, f"Download failed: {error_msg}", True)

    def _get_common_ydl_opts(self) -> Dict[str, Any]:
        """Get common yt-dlp options with anti-bot detection measures"""
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            # User agent rotation
            "user_agent": random.choice(USER_AGENTS),
            # Retry logic
            "extractor_retries": 5,
            "fragment_retries": 10,
            "retries": 10,
            # Sleep intervals to avoid rate limiting
            "sleep_interval": self.sleep_interval[0],
            "max_sleep_interval": self.sleep_interval[1],
            "sleep_interval_requests": 1.0,
            "sleep_interval_subtitles": 0.5,
            # Geo-bypass
            "geo_bypass": True,
            "geo_bypass_country": "US",
            # Additional headers
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
            },
        }

        # Add cookies if provided
        if self.cookies_file and os.path.exists(self.cookies_file):
            opts["cookiefile"] = self.cookies_file
            logger.info(f"Using cookies from {self.cookies_file}")

        # Add download archive to skip already downloaded videos
        if self.use_download_archive:
            opts["download_archive"] = self.archive_file

        return opts

    def is_url_duplicate(self, url: str) -> Optional[str]:
        """Check if URL is already queued or downloading. Returns job_id if duplicate."""
        if self.allow_duplicates:
            return None

        normalized = self.normalize_url(url)
        for job_id, job in self.jobs.items():
            if job.status in ["queued", "downloading"]:
                if self.normalize_url(job.url) == normalized:
                    return job_id
        return None

    def get_video_info(
        self, url: str, cookies_file: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract video metadata without downloading"""
        if yt_dlp is None:
            logger.error("yt-dlp not available")
            return None

        try:
            ydl_opts = self._get_common_ydl_opts()
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts["cookiefile"] = cookies_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[misc]
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "uploader": info.get("uploader", "Unknown"),
                    "upload_date": info.get("upload_date", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                }
        except Exception as e:
            logger.error(f"Failed to extract info for {url}: {e}")
            return None

    def progress_hook(self, job_id: str) -> Callable[[Dict[str, Any]], None]:
        """Create a progress hook for yt-dlp"""

        def hook(d: Dict[str, Any]) -> None:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]

            if d["status"] == "downloading":
                job.status = "downloading"
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)

                if total and total > 0:
                    job.progress = min(int((downloaded / total) * 100), 100)
                    job.total_bytes = int(total)
                    job.downloaded_bytes = int(downloaded)
                elif "_percent_str" in d:
                    percent_str = d["_percent_str"].strip().rstrip("%")
                    try:
                        job.progress = min(int(float(percent_str)), 100)
                    except (ValueError, TypeError):
                        pass

                job.speed = d.get("speed")
                job.eta = d.get("eta")

                if "filename" in d:
                    job.filename = os.path.basename(d["filename"])

            elif d["status"] == "finished":
                job.progress = 100
                job.speed = None
                job.eta = None
                if "filename" in d:
                    job.filename = os.path.basename(d["filename"])

            elif d["status"] == "error":
                job.status = "failed"
                job.error = "Download failed"
                job.completed_at = datetime.now()

        return hook

    def postprocessor_hook(self, job_id: str) -> Callable[[Dict[str, Any]], None]:
        """Create a postprocessor hook to mark true completion"""

        def hook(d: Dict[str, Any]) -> None:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]
            if d.get("status") == "finished":
                job.status = "completed"
                job.progress = 100
                job.completed_at = datetime.now()

        return hook

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between downloads"""
        with self.download_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_download_time

            if time_since_last < self.rate_limit_seconds:
                sleep_time = self.rate_limit_seconds - time_since_last
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

            self.last_download_time = time.time()

    def download_video(self, url: str, job_id: str, cookies_file: Optional[str] = None) -> None:
        """Download a single video with custom naming"""
        job = self.jobs[job_id]

        if yt_dlp is None:
            logger.error("yt-dlp not available")
            job.status = "failed"
            job.error = "yt-dlp not available"
            job.completed_at = datetime.now()
            return

        try:
            # Apply rate limiting before starting download
            self._apply_rate_limit()

            # Extract video info first
            info = self.get_video_info(url, cookies_file=cookies_file)
            if not info:
                job.status = "failed"
                job.error = "Failed to extract video information"
                job.completed_at = datetime.now()
                return

            # Sanitize title for filesystem
            safe_title = self.sanitize_filename(info["title"])

            # Format upload date
            upload_date = info["upload_date"]
            if upload_date and len(upload_date) >= 8:
                formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            else:
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            # Create output template for the specific naming format
            # /specified_folder/video-title-yyyy-mm-dd/video-title-yyyy-mm-dd.mp4
            folder_name = f"{safe_title}-{formatted_date}"
            output_template = os.path.join(
                self.download_dir, folder_name, f"{safe_title}-{formatted_date}.%(ext)s"
            )

            # Ensure the directory exists
            output_dir = os.path.join(self.download_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)

            # Start with common options and add download-specific ones
            ydl_opts = self._get_common_ydl_opts()
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts["cookiefile"] = cookies_file
            ydl_opts.update(
                {
                    "format": (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                        "/bestvideo+bestaudio"
                        "/best[ext=mp4]"
                        "/best"
                    ),
                    "merge_output_format": "mp4",
                    "outtmpl": output_template,
                    "progress_hooks": [self.progress_hook(job_id)],
                    "postprocessor_hooks": [self.postprocessor_hook(job_id)],
                    "extractaudio": False,
                    "audioformat": "mp3",
                    "embed_subs": False,
                    "writesubtitles": False,
                    "writeautomaticsub": False,
                    "nooverwrites": not self.overwrite_existing,
                }
            )

            job.status = "downloading"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[misc]
                result = ydl.download([url])
                if result == 0:
                    if job.status == "downloading" and job.progress == 0:
                        job.status = "skipped"
                        job.error = "Already downloaded (found in archive)"
                        job.completed_at = datetime.now()
                        logger.info(f"Skipped {url} - already in archive")
                    elif job.status != "completed":
                        job.status = "completed"
                        job.progress = 100
                        job.completed_at = datetime.now()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Download failed for {url}: {error_msg}")

            # Classify the error
            error_type, suggestion, is_retryable = self.classify_error(error_msg)

            job.status = "failed"
            job.error = error_msg
            job.error_type = error_type
            job.error_suggestion = suggestion
            job.is_retryable = is_retryable
            job.completed_at = datetime.now()

            # Log with classification
            logger.error(
                f"Error type: {error_type.value}, "
                f"Retryable: {is_retryable}, "
                f"Suggestion: {suggestion}"
            )
        finally:
            if cookies_file and cookies_file.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(cookies_file)
                except OSError:
                    pass

    def _write_cookies_file(self, cookies: List[Dict[str, Any]]) -> Optional[str]:
        """Write browser cookies to a Netscape-format temp file for yt-dlp."""
        if not cookies:
            return None

        fd, path = tempfile.mkstemp(suffix=".txt", prefix="ytdlp_cookies_")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for c in cookies:
                    domain = c.get("domain", "")
                    include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
                    path_val = c.get("path", "/")
                    secure = "TRUE" if c.get("secure") else "FALSE"
                    expires = str(int(c.get("expirationDate", 0)))
                    name = c.get("name", "")
                    value = c.get("value", "")
                    f.write(
                        f"{domain}\t{include_subdomains}\t{path_val}\t"
                        f"{secure}\t{expires}\t{name}\t{value}\n"
                    )
        except Exception as e:
            logger.error(f"Failed to write cookies file: {e}")
            try:
                os.unlink(path)
            except OSError:
                pass
            return None

        return path

    def queue_download(self, url: str, cookies_file: Optional[str] = None) -> tuple[str, bool]:
        """Queue a download and return (job_id, is_new). is_new=False if duplicate."""
        duplicate_job_id = self.is_url_duplicate(url)
        if duplicate_job_id:
            logger.info(f"URL already queued/downloading: {url} (job {duplicate_job_id})")
            return (duplicate_job_id, False)

        job_id = str(uuid.uuid4())
        job = DownloadStatus(job_id, url)
        self.jobs[job_id] = job

        self.executor.submit(self.download_video, url, job_id, cookies_file)

        return (job_id, True)

    def queue_multiple_downloads(
        self, urls: List[str], cookies: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Queue multiple downloads and return results with duplicate info"""
        cookies_file = self._write_cookies_file(cookies) if cookies else None

        results = {"job_ids": [], "new_count": 0, "duplicate_count": 0, "duplicates": []}

        for url in urls:
            url = url.strip()
            if url:
                job_id, is_new = self.queue_download(url, cookies_file)
                results["job_ids"].append(job_id)
                if is_new:
                    results["new_count"] += 1
                else:
                    results["duplicate_count"] += 1
                    results["duplicates"].append({"url": url, "job_id": job_id})

        return results

    def get_job_status(self, job_id: str) -> Optional[DownloadStatus]:
        """Get status of a specific job"""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, DownloadStatus]:
        """Get status of all jobs"""
        return self.jobs.copy()

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> None:
        """Remove old completed/failed jobs"""
        now = datetime.now()
        to_remove: List[str] = []

        for job_id, job in self.jobs.items():
            if job.status in ["completed", "failed"] and job.completed_at:
                age = (now - job.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(job_id)

        for job_id in to_remove:
            del self.jobs[job_id]

        logger.info(f"Cleaned up {len(to_remove)} old jobs")
