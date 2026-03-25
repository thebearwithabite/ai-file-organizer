## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.

## 2024-03-25 - ARIA labels for icon-only buttons
**Learning:** Icon-only buttons with decorative visual elements (like Lucide React SVG icons) need an explicit `aria-label` for screen readers, and the inner icon must have `aria-hidden="true"` to prevent duplicate or confusing announcements. Focus states using `focus-visible` enhance keyboard accessibility.
**Action:** Always pair `aria-label` and `title` on icon-only `<button>` tags and add `aria-hidden="true"` to the child icon element.
