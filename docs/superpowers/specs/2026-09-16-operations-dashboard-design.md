# Operations Dashboard Design

## Approved reference

Implement the user-approved Option A Operations Dashboard using the selected Nowlert mockup as the visual acceptance reference. The dashboard must preserve the existing Nowlert shell/sidebar and replace only the Dashboard content and Dashboard-specific topbar treatment.

## Dashboard information architecture

- KPI row: Integrations, Destinations, Routes, Success Rate, Failures.
- Main row: Delivery Performance chart and Recent Activity.
- Insight row: Top Integrations, Top Destinations, System Health.
- Bottom configuration strip: API Tokens, Active Filters, Shared Destinations, Audit Issues.
- Dashboard range controls remain synchronized and use existing dashboard history windows.
- The dashboard must use real visible user data; it must not invent configuration or delivery values.
- Live delivery/audit/filter data refreshes every 30 seconds while Dashboard is active.

## Routing Flow

- Keep existing dedicated Routing Flow behavior unchanged.
- Add Last 3 hours and Last 6 hours between Last hour and Last 24 hours.
- Backend range validation must support 3h and 6h.

## Retirement

The legacy Source → Route → Destination Routing Flow panel inside Dashboard is superseded by the dedicated Routing Flow menu. It must not render or be called by the new Dashboard renderer.

## Isolation

Use a new WebUI layer (`operations_dashboard.js` / `operations_dashboard.css`) loaded after the accepted Routing Flow and Filtering layers, so the existing Destinations, Filtering, Routing Flow, ingestion, delivery, and access behavior remains untouched.
