# Client Demo Guide

## Product Overview

CounterOS is a local-first POS appliance MVP for hospital counter billing. It
keeps core counter work usable on the local terminal and stores data locally.

## What The Demo Proves

- Cashier login
- Cashier session opening and closing
- Patient creation
- Catalog service selection
- Draft billing with autosave
- Cash bill finalization
- Receipt generation
- Development-mode receipt printing
- Local sync retry foundation
- Recovery scan foundation
- Daily reports
- Settings, support bundle, and audit log visibility

## Offline-First Behavior

The local SQLite database is the durable source for the terminal. Drafts,
final bills, payments, receipts, sync events, print jobs, and audit logs are
stored locally.

## Recovery

Recovery scans identify work that may need review, such as open cashier
sessions, open drafts, unsynced bills, and print jobs. Recovery does not
silently change business records.

## Printing In Demo Mode

Printing uses a development printer adapter. It creates and records print jobs
without claiming real hardware printing.

## Sync In Demo Mode

Sync uses a development adapter. Manual retry marks local events as synced for
demo purposes. Real cloud sync requires a production endpoint decision.

## Intentionally Not Part Of MVP

Refunds, final bill void, gateway payments, real cloud sync, real printer
hardware integration, pharmacy inventory, lab workflow, advanced analytics,
and kiosk auto-install.

## Recommended Production Decisions

- Printer hardware and receipt format
- Cloud sync endpoint and retry policy
- User and role model
- Backup location and restore process
- Linux appliance hardware
- UPS/power backup plan
