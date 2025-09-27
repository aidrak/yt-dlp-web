#!/bin/bash
set -e

# Get environment variables with defaults (99:100 is nobody:users - standard for Unraid)
PUID=${PUID:-99}
PGID=${PGID:-100}

# Only run permission setup if we're root (for initial setup)
if [ "$(id -u)" = "0" ]; then
    echo "Setting up permissions for PUID=$PUID, PGID=$PGID"

    # Create group if it doesn't exist
    if ! getent group "$PGID" > /dev/null 2>&1; then
        groupadd -g "$PGID" appgroup
    fi

    # Create or use existing user
    if ! getent passwd "$PUID" > /dev/null 2>&1; then
        # No user with this UID exists, create one
        useradd --create-home --shell /bin/bash --uid "$PUID" --gid "$PGID" appuser
    fi

    # Ensure downloads directory exists and has correct permissions
    mkdir -p /downloads
    chown -R "$PUID:$PGID" /downloads
    chmod -R 755 /downloads

    # Ensure app directory has correct permissions
    chown -R "$PUID:$PGID" /app

    # Switch to the app user and re-exec
    exec gosu "$PUID:$PGID" "$0" "$@"
fi

# If we're here, we're running as the app user
# Check if downloads directory is writable
if [ ! -w "/downloads" ]; then
    echo "Warning: /downloads directory is not writable"
    echo "Please check your volume mount permissions"
    echo "Try: docker run ... -e PUID=$(id -u) -e PGID=$(id -g) ..."
fi

# Execute the main command
exec "$@"