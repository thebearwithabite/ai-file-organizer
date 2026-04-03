## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.

## 2024-05-20 - Accessible Cycling Text Elements
**Learning:** Dynamically changing text elements (like cycling loading messages) are silently updated and ignored by screen readers, leaving visually impaired users unaware of progress or status changes.
**Action:** Always apply `aria-live="polite"` and `aria-atomic="true"` to dynamically updating text containers to ensure screen readers announce the changing content without unnecessarily interrupting the user.
