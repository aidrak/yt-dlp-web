import logging
import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from .downloader import YTDLPDownloader

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app with correct template and static paths
import os as _os
app = Flask(__name__,
           template_folder=_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'templates'),
           static_folder=_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'static'))

# Configuration
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/downloads')
PORT = int(os.getenv('PORT', 8000))
MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 2))
RATE_LIMIT_SECONDS = float(os.getenv('RATE_LIMIT_SECONDS', '3.0'))
SLEEP_INTERVAL_MIN = float(os.getenv('SLEEP_INTERVAL_MIN', '1.0'))
SLEEP_INTERVAL_MAX = float(os.getenv('SLEEP_INTERVAL_MAX', '3.0'))
COOKIES_FILE = os.getenv('COOKIES_FILE', '').strip() or None
ALLOW_DUPLICATES = os.getenv('ALLOW_DUPLICATES', 'false').lower() == 'true'
OVERWRITE_EXISTING = os.getenv('OVERWRITE_EXISTING', 'false').lower() == 'true'
USE_DOWNLOAD_ARCHIVE = os.getenv('USE_DOWNLOAD_ARCHIVE', 'true').lower() == 'true'

# Ensure download directory exists and is writable
try:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    logger.info(f"Download directory ready: {DOWNLOAD_DIR}")

    # Test write permissions (non-fatal for container startup)
    test_file = os.path.join(DOWNLOAD_DIR, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("Download directory is writable")
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.warning(f"Download directory write test failed: {e}")
        logger.warning("Downloads may fail - check volume mount permissions")

except Exception as e:
    logger.error(f"Failed to setup download directory {DOWNLOAD_DIR}: {e}")
    # Don't raise - let the app start so we can show error in health check

# Initialize downloader with anti-bot detection and duplicate handling
downloader = YTDLPDownloader(
    DOWNLOAD_DIR,
    rate_limit_seconds=RATE_LIMIT_SECONDS,
    sleep_interval=(SLEEP_INTERVAL_MIN, SLEEP_INTERVAL_MAX),
    cookies_file=COOKIES_FILE,
    allow_duplicates=ALLOW_DUPLICATES,
    overwrite_existing=OVERWRITE_EXISTING,
    use_download_archive=USE_DOWNLOAD_ARCHIVE
)

# Cleanup thread to remove old jobs
def cleanup_worker():
    while True:
        time.sleep(3600)  # Run every hour
        downloader.cleanup_old_jobs(24)  # Remove jobs older than 24 hours

cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Handle download requests"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        urls = data.get('urls', [])
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400

        # Handle single URL string
        if isinstance(urls, str):
            urls = [urls]

        # Filter and validate URLs
        valid_urls = []
        for url in urls:
            url = url.strip()
            if url and (url.startswith('http://') or url.startswith('https://')):
                valid_urls.append(url)

        if not valid_urls:
            return jsonify({'error': 'No valid URLs provided'}), 400

        # Queue downloads
        results = downloader.queue_multiple_downloads(valid_urls)

        logger.info(f"Queued {results['new_count']} new downloads, {results['duplicate_count']} duplicates")

        response = {
            'success': True,
            'job_ids': results['job_ids'],
            'new_count': results['new_count'],
            'duplicate_count': results['duplicate_count'],
            'message': f"Queued {results['new_count']} new downloads"
        }

        if results['duplicate_count'] > 0:
            response['message'] += f", {results['duplicate_count']} duplicates skipped"
            response['duplicates'] = results['duplicates']

        return jsonify(response)

    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    """Get status of a specific download job"""
    try:
        job = downloader.get_job_status(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        response = {
            'job_id': job.job_id,
            'url': job.url,
            'status': job.status,
            'progress': job.progress,
            'filename': job.filename,
            'error': job.error,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }

        # Add error details if available
        if job.error_type:
            response['error_type'] = job.error_type.value
            response['error_suggestion'] = job.error_suggestion
            response['is_retryable'] = job.is_retryable

        return jsonify(response)

    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_all_status():
    """Get status of all download jobs"""
    try:
        jobs = downloader.get_all_jobs()
        job_list = []

        for job in jobs.values():
            job_data = {
                'job_id': job.job_id,
                'url': job.url,
                'status': job.status,
                'progress': job.progress,
                'filename': job.filename,
                'error': job.error,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            }

            # Add error details if available
            if job.error_type:
                job_data['error_type'] = job.error_type.value
                job_data['error_suggestion'] = job.error_suggestion
                job_data['is_retryable'] = job.is_retryable

            job_list.append(job_data)

        return jsonify({
            'jobs': job_list,
            'total': len(job_list)
        })

    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        info = downloader.get_video_info(url)
        if not info:
            return jsonify({'error': 'Failed to extract video information'}), 400

        return jsonify({
            'success': True,
            'info': info
        })

    except Exception as e:
        logger.error(f"Info error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint for Docker"""
    try:
        # Check if download directory is writable
        writable = False
        try:
            test_file = os.path.join(DOWNLOAD_DIR, '.health_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            writable = True
        except:
            pass

        status = 'healthy' if writable else 'degraded'

        response = {
            'status': status,
            'download_dir': DOWNLOAD_DIR,
            'download_dir_exists': os.path.exists(DOWNLOAD_DIR),
            'download_dir_writable': writable,
            'active_jobs': len([
                j for j in downloader.get_all_jobs().values()
                if j.status in ['queued', 'downloading']
            ])
        }

        if not writable:
            response['warning'] = 'Download directory is not writable. Check volume permissions (PUID/PGID).'

        return jsonify(response)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main entry point for the application."""
    logger.info(f"Starting yt-dlp web server on port {PORT}")
    logger.info(f"Download directory: {DOWNLOAD_DIR}")

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )


if __name__ == '__main__':
    main()
