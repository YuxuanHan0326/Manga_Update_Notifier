# Requirements

## Document Status
- Version: v0.2
- Last Updated: 2026-03-09
- Source: user-confirmed requirements from kickoff discussion

## Functional Requirements

### FR-001 Source Adapter Framework
System must support pluggable source adapters for different websites.
Acceptance:
- New source can be added by implementing a defined adapter interface.
- Core scheduler and notification logic do not require source-specific edits.

### FR-002 CopyManga Source (Phase 1)
System must support CopyManga as the first adapter.
Acceptance:
- Can search content from CopyManga.
- Can query chapters/updates for subscribed items.

### FR-003 Subscription Management
System must allow managing tracked items in Web UI.
Acceptance:
- Create, edit, pause/resume, delete subscription.
- Persist subscription state across restarts.
- Provide temporary per-subscription debug actions for notification test and update simulation.
- Debug simulation must not affect normal automatic daily-summary notification behavior.
- Subscription list should display Last Seen time and Last Seen latest-chapter title.
- New subscription should prefill Last Seen fields from available search metadata when possible.

### FR-004 Search and One-Click Subscribe
System must provide in-app search and one-click add to tracking.
Acceptance:
- User enters keyword and sees search results.
- Search results should support pagination.
- Search results should display cover image and basic metadata.
- Search results should display latest update time and latest chapter info when metadata can be obtained.
- Clicking an item creates a valid subscription record automatically.

### FR-005 Scheduled Update Check
System must run update checks on configurable schedule.
Acceptance:
- User can configure check frequency in UI.
- Timezone should support auto-detection by client IP (with fallback if lookup fails).
- Timezone should support manual selection from a timezone list in UI.
- Check jobs execute automatically with logs and status.

### FR-006 Daily Summary Notification
System must send one daily summary at a configured time.
Acceptance:
- Summary includes all new updates since last summary window.
- Summary can be delivered through configured notification channel(s).
- If there are no real updates in the current window, automatic push should not be sent.
- If service downtime/restart spans summary boundary, previously unsent real updates must still be included in the next successful summary.

### FR-007 Notification Channel Abstraction
System must support pluggable notification backends.
Acceptance:
- At least one channel is enabled in Phase 1.
- Channel interface allows future providers without core rewrite.

### FR-008 Docker Deployment
System must be deployable with Docker on NAS.
Acceptance:
- Compose-based startup works.
- Config and data are persisted via mounted volumes.

## Non-Functional Requirements

### NFR-001 Reliability
- Service should continue running after source-level transient errors.
- No process exit on recoverable adapter errors.

### NFR-002 Maintainability
- Clear module boundaries: core, adapters, notifications, API, UI.
- Project memory and decision history maintained in markdown docs.

### NFR-003 Observability
- Structured logs for scheduler, adapter calls, notifications, and failures.
- Recent logs visible from Web UI.

### NFR-004 Performance
- Phase 1 target: support at least 200 subscriptions on single NAS instance.
- Update check duration should remain bounded via batching/pagination.

### NFR-005 Security (Baseline)
- Config secrets stored outside source code.
- Deployment guidance must include reverse-proxy/auth recommendation.

## Business Rules
- BR-001 Update detection is based on adapter-defined unique update ID.
- BR-002 Daily summary window uses configured timezone.
- BR-003 Duplicate updates must not be notified twice in same window.
- BR-004 Adapter failures for one source must not block other sources.
- BR-005 Debug/simulated updates are excluded from daily-summary auto push window.
- BR-006 Summary candidate window is based on unsummarized real events (not strict calendar-day cutoff) to avoid missed notifications after downtime.

## Out of Scope (Current)
- Content downloading/export workflow
- Rich analytics dashboard
- Distributed worker cluster

## Assumptions
- Single user or single household usage in Phase 1.
- User can provide legal/technical access credentials if required by a source.

## Missing Information
- Expected peak scale (subscriptions, check frequency).
