# Project Brief

## Project Name
Manga Update Notifier (working title)

## Background
Build a self-hosted service for NAS that monitors content updates from multiple sites and sends summary notifications.

## Primary Goal
Deliver a Docker-first web application that:
- Tracks subscribed comics/content items
- Checks updates on schedule
- Sends daily summary notifications at a fixed time
- Starts with CopyManga support
- Can be extended to many different sites in the future

## Scope (Phase 1)
- Source support: CopyManga
- Subscription management via Web UI
- Search in UI and one-click subscription creation
- Scheduled update checks
- Daily summary notification delivery
- Docker deployment for NAS

## Success Criteria
- User can deploy with Docker on NAS and open Web UI
- User can search CopyManga in UI and add a subscription without manual ID editing
- Service detects new chapters for subscribed items
- Service sends one daily summary notification at configured time
- System keeps running stably for 7+ days without manual restart

## Non-Goals (Phase 1)
- Downloading chapter images or packaging CBZ/PDF
- Full account system / multi-tenant auth
- Mobile app client
- Supporting all target sites in first release

## Constraints
- Must run in containerized NAS environment
- Must keep architecture extensible for heterogeneous sites
- Must persist project memory in markdown files

## Stakeholder Intent (Confirmed)
- New project from zero (not patching old downloader as main path)
- Existing two repositories are references only

## Open Items
- Expected peak scale for capacity planning and stress testing thresholds
