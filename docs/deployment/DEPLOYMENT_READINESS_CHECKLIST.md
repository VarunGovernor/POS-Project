# Deployment Readiness Checklist

## Operating System

- [ ] Linux target selected
- [ ] systemd available
- [ ] Chromium or approved kiosk browser available

## Runtime

- [ ] Python version selected and installed
- [ ] Node version selected and installed
- [ ] npm available
- [ ] SQLite available

## Storage

- [ ] SQLite storage path selected
- [ ] Data directory selected
- [ ] Backup directory selected
- [ ] Log directory selected
- [ ] Directory permissions reviewed

## Decisions

- [ ] Printer hardware decision made
- [ ] Real printer adapter planned
- [ ] Cloud sync endpoint decision made
- [ ] User/role decision made
- [ ] Receipt format decision made
- [ ] Support access decision made
- [ ] Kiosk mode decision made
- [ ] Power backup/UPS recommendation reviewed

## Validation

- [ ] `os/install/validate-host.sh` run on target
- [ ] `scripts/install/validate-runtime-files.sh` passes
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Frontend build passes

This package is deployment readiness only. It does not claim production
deployment is complete.
