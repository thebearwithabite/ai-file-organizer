## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.

## 2024-03-30 - Screen Reader Accessibility for Icon-Only Action Buttons
**Learning:** Action buttons composed exclusively of decorative or functional icons (e.g., Lucide React icons like X, Loader2, Check) inside of status/preview dialogs often lack sufficient text context, causing screen readers to announce them cryptically as just "button".
**Action:** Always apply an `aria-label` or `title` containing a clear description (e.g., "Skip organization") to the parent `<button>`, and explicitly set `aria-hidden="true"` on the child `<svg>` icon element to prevent conflicting or duplicate screen reader announcements.
