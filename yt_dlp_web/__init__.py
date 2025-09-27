"""yt-dlp-web: Web frontend for yt-dlp with custom naming and Docker support."""

__version__ = "0.1.0"
__author__ = "aidrak"
__description__ = "Web frontend for yt-dlp with custom naming and Docker support"

from .downloader import YTDLPDownloader, DownloadStatus

__all__ = ["YTDLPDownloader", "DownloadStatus"]