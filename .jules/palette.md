## 2024-05-23 - Icon-Only Button Accessibility Pattern
**Learning:** Several icon-only buttons (notifications, user menu, undo) lacked accessible names, relying solely on visual icons. This is a recurring pattern in the dashboard components.
**Action:** When creating or modifying icon-only buttons, always include both `aria-label` (for screen readers) and `title` (for mouse hover tooltips) to ensure inclusive access.
