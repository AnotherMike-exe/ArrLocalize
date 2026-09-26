#!/bin/sh
# Runs as root. Gives /config to PUID:PGID, then starts supervisord.
# It never changes the owner of /media or the debrid mount.
set -e

mkdir -p /config/history
chown "${PUID}:${PGID}" /config /config/history

exec /usr/bin/supervisord -c /etc/supervisord.conf
