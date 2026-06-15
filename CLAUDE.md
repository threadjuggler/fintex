# Project rules for Claude

- **Always ask for decisions.** When a task involves a choice that isn't trivially
  obvious — architecture, naming, scope, dependencies, data models, deleting/overwriting,
  anything outward-facing — stop and ask the user before deciding. Prefer a quick question
  over assuming a default.
- **Always ask when something is unclear.** If a request is ambiguous, underspecified,
  or could reasonably be interpreted in more than one way, ask the user to clarify before
  acting. Never guess at intent — a short clarifying question is always preferred over
  proceeding on an assumption.
