from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime
from threading import Thread
from typing import Any, Callable, Dict, List, Optional

try:
    import yt_dlp  # type: ignore[import-untyped]
except ImportError:
    yt_dlp = None

logger = logging.getLogger(__name__)

class DownloadStatus:
    def __init__(self, job_id: str, url: str):
        self.job_id = job_id
        self.url = url
        self.status = "queued"  # queued, downloading, completed, failed
        self.progress = 0
        self.filename: Optional[str] = None
        self.error: Optional[str] = None
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None

class YTDLPDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.jobs: Dict[str, DownloadStatus] = {}

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
        # Remove multiple consecutive dashes and spaces
        filename = re.sub(r'[-\s]+', '-', filename)
        # Remove leading/trailing dashes and spaces
        filename = filename.strip('- ')
        return filename

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract video metadata without downloading"""
        if yt_dlp is None:
            logger.error("yt-dlp not available")
            return None

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[misc]
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                }
        except Exception as e:
            logger.error(f"Failed to extract info for {url}: {e}")
            return None

    def progress_hook(self, job_id: str) -> Callable[[Dict[str, Any]], None]:
        """Create a progress hook for yt-dlp"""
        def hook(d: Dict[str, Any]) -> None:
            if job_id in self.jobs:
                job = self.jobs[job_id]

                if d['status'] == 'downloading':
                    job.status = "downloading"
                    if 'total_bytes' in d and d['total_bytes']:
                        job.progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                    elif '_percent_str' in d:
                        # Parse percentage from string like "50.0%"
                        percent_str = d['_percent_str'].strip().rstrip('%')
                        try:
                            job.progress = int(float(percent_str))
                        except (ValueError, TypeError):
                            pass

                    # Extract filename if available
                    if 'filename' in d:
                        job.filename = os.path.basename(d['filename'])

                elif d['status'] == 'finished':
                    job.status = "completed"
                    job.progress = 100
                    job.completed_at = datetime.now()
                    if 'filename' in d:
                        job.filename = os.path.basename(d['filename'])

                elif d['status'] == 'error':
                    job.status = "failed"
                    job.error = "Download failed"
                    job.completed_at = datetime.now()

        return hook

    def download_video(self, url: str, job_id: str) -> None:
        """Download a single video with custom naming"""
        job = self.jobs[job_id]

        if yt_dlp is None:
            logger.error("yt-dlp not available")
            job.status = "failed"
            job.error = "yt-dlp not available"
            job.completed_at = datetime.now()
            return

        try:
            # Extract video info first
            info = self.get_video_info(url)
            if not info:
                job.status = "failed"
                job.error = "Failed to extract video information"
                job.completed_at = datetime.now()
                return

            # Sanitize title for filesystem
            safe_title = self.sanitize_filename(info['title'])

            # Format upload date
            upload_date = info['upload_date']
            if upload_date and len(upload_date) >= 8:
                formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            else:
                formatted_date = datetime.now().strftime("%Y-%m-%d")

            # Create output template for the specific naming format
            # /specified_folder/video-title-yyyy-mm-dd/video-title-yyyy-mm-dd.mp4
            folder_name = f"{safe_title}-{formatted_date}"
            output_template = os.path.join(
                self.download_dir,
                folder_name,
                f"{safe_title}-{formatted_date}.%(ext)s"
            )

            # Ensure the directory exists
            output_dir = os.path.join(self.download_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)

            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # Prefer mp4, fallback to best
                'outtmpl': output_template,
                'progress_hooks': [self.progress_hook(job_id)],
                'no_warnings': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'nooverwrites': False,  # Allow overwriting existing files to prevent (1) suffix
            }

            job.status = "downloading"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[misc]
                ydl.download([url])

        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now()

    def queue_download(self, url: str) -> str:
        """Queue a download and return job ID"""
        job_id = str(uuid.uuid4())
        job = DownloadStatus(job_id, url)
        self.jobs[job_id] = job

        # Start download in background thread
        thread = Thread(target=self.download_video, args=(url, job_id))
        thread.daemon = True
        thread.start()

        return job_id

    def queue_multiple_downloads(self, urls: List[str]) -> List[str]:
        """Queue multiple downloads and return list of job IDs"""
        job_ids = []
        for url in urls:
            url = url.strip()
            if url:  # Skip empty lines
                job_id = self.queue_download(url)
                job_ids.append(job_id)
        return job_ids

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
