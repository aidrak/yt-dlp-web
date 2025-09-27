# yt-dlp Web Downloader

A containerized web interface for yt-dlp that downloads videos with custom naming format, perfect for Unraid deployment.

## Features

- 🎥 **Clean web interface** for single or bulk URL downloads
- 📁 **Custom naming format**: `video-title-yyyy-mm-dd/video-title-yyyy-mm-dd.mp4`
- 📊 **Real-time progress tracking** with status updates
- 🔄 **Background downloads** with job management
- 🐳 **Docker containerized** with health checks
- 🖥️ **Unraid ready** with template included
- 🎯 **Multi-platform support** (YouTube, Vimeo, Twitter, etc.)
- ⚡ **MP4 format preference** with automatic fallbacks

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Unraid (for production deployment)

### Development Setup
1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd yt-dlp-web
   cp .env.example .env
   # Edit .env with your actual values
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface:**
   - Open http://localhost:8000
   - Add video URLs (one per line)
   - Click "Start Downloads"

## Unraid Deployment

### Quick Install
1. **Add the template:**
   - Copy `unraid-template.xml` to your Unraid templates
   - Or manually create a new container with the settings below

2. **Container Configuration:**
   ```
   Repository: yt-dlp-web:latest
   Network Type: bridge
   Port: 8000:8000
   ```

3. **Volume Mapping:**
   ```
   Host Path: /mnt/user/downloads/yt-dlp
   Container Path: /downloads
   ```

4. **Environment Variables:**
   ```
   PORT=8000
   DOWNLOAD_DIR=/downloads
   MAX_CONCURRENT_DOWNLOADS=2
   DEBUG=false
   ENVIRONMENT=production
   PUID=99
   PGID=100
   ```

### Configuration with .env File

For Docker Compose, create a `.env` file to customize settings:

```bash
# Copy the example file
cp .env.docker .env

# Edit settings
nano .env
```

**Example .env file:**
```bash
PORT=9000                    # Change web interface port
DOWNLOAD_DIR=/downloads      # Download directory
MAX_CONCURRENT_DOWNLOADS=3   # Max simultaneous downloads
PUID=1000                   # Your user ID (run: id -u)
PGID=1000                   # Your group ID (run: id -g)
ENVIRONMENT=production
DEBUG=false
```

Then run: `docker-compose up -d`

### Custom Download Directory
Configure the `DOWNLOAD_DIR` environment variable to match your preferred Unraid share:
- `/mnt/user/Media/YouTube/`
- `/mnt/user/downloads/videos/`
- `/mnt/cache/downloads/` (for cache-only downloads)

## Usage

### Web Interface
1. **Access**: Navigate to `http://your-unraid-ip:8000`
2. **Add URLs**: Paste video URLs (supports multiple lines)
3. **Preview**: Click "Preview Info" to see video details
4. **Download**: Click "Start Downloads" to begin
5. **Monitor**: Watch real-time progress and status

### Supported URLs
- YouTube videos and playlists
- Vimeo videos
- Twitter/X videos
- Facebook videos
- Instagram videos
- TikTok videos
- And 1000+ other sites supported by yt-dlp

### File Organization
Downloads are organized as:
```
/your-download-dir/
├── My-Great-Video-2024-01-15/
│   └── My-Great-Video-2024-01-15.mp4
├── Another-Video-2024-01-16/
│   └── Another-Video-2024-01-16.mp4
└── ...
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOWNLOAD_DIR` | Target download directory | `/downloads` |
| `PORT` | Web interface port | `8000` |
| `MAX_CONCURRENT_DOWNLOADS` | Simultaneous downloads | `2` |
| `DEBUG` | Enable debug logging | `false` |
| `ENVIRONMENT` | Runtime environment | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### Advanced Configuration
- **Concurrent Downloads**: Adjust based on your network and storage
- **Custom Formats**: Modify `downloader.py` for different naming schemes
- **Quality Settings**: Edit yt-dlp options in the downloader module

## API Endpoints

- `GET /` - Web interface
- `POST /download` - Queue downloads
- `GET /status/<job_id>` - Check specific job status
- `GET /status` - Get all job statuses
- `POST /info` - Get video info without downloading
- `GET /health` - Health check endpoint

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Run with auto-reload
DEBUG=true python app.py
```

### Building Custom Image
```bash
# Build the image
docker build -t yt-dlp-web:latest .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v /your/downloads:/downloads \
  -e DOWNLOAD_DIR=/downloads \
  yt-dlp-web:latest
```

### Code Quality
```bash
# Format and lint code
ruff format .
ruff check .
```

## Troubleshooting

### Common Issues
1. **Permission Errors**: Ensure download directory is writable
2. **Network Errors**: Check if the video URLs are accessible
3. **Format Errors**: Some videos may not have MP4 versions available
4. **Disk Space**: Monitor available storage space

### Health Check
Visit `/health` endpoint to verify:
- Application status
- Download directory accessibility
- Active download count

### Logs
```bash
# View container logs
docker logs yt-dlp-web

# Follow logs in real-time
docker logs -f yt-dlp-web
```

## Project Structure

```
yt-dlp-web/
├── app.py                # Main Flask application
├── downloader.py         # yt-dlp wrapper and logic
├── templates/
│   └── index.html       # Web interface
├── static/
│   ├── style.css        # Styles
│   └── script.js        # Frontend JavaScript
├── Dockerfile           # Container definition
├── docker-compose.yml   # Development setup
├── unraid-template.xml  # Unraid template
├── requirements.txt     # Python dependencies
└── .env.example        # Environment template
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Ensure code quality: `ruff format . && ruff check .`
5. Update documentation if needed
6. Commit: `git commit -m "Add feature"`
7. Push: `git push origin feature-name`
8. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Built with ❤️ using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [Claude Code](https://claude.ai/code)