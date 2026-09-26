#!/bin/sh
# Started by supervisord. Applies UMASK and drops to PUID:PGID before the loop.
umask "${UMASK}"
exec su-exec "${PUID}:${PGID}" arr-localize loop
