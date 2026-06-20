# Local Linux Deployment Notes

## Files

- Environment template: `os/install/counteros.env.example`
- API service template: `os/systemd/counteros-api.service`
- Frontend service template: `os/systemd/counteros-frontend.service`
- Kiosk service template: `os/systemd/counteros-kiosk.service`
- Kiosk launcher: `os/kiosk/launch-kiosk.sh`

## Manual Outline

1. Copy project to `/opt/counteros`.
2. Create `/etc/counteros/counteros.env` from the example.
3. Create data and log directories.
4. Install backend Python dependencies.
5. Install frontend Node dependencies and build frontend.
6. Review systemd service templates.
7. Copy templates to `/etc/systemd/system/` only after review.
8. Use `systemctl` manually to enable/start services.

No script in this repository performs automatic system install.
