## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.
## 2024-05-23 - Keyboard Accessible Tooltips
**Learning:** Using `group-hover` on tooltips without focus states makes them inaccessible to keyboard users.
**Action:** Wrap the tooltip trigger icon in a focusable `<button type="button" className="peer focus-visible:ring-2 focus-visible:ring-background/50 focus-visible:outline-none" aria-label="More information">`, add `aria-hidden="true"` to the icon, and use `peer-hover:visible peer-focus:visible` on the tooltip container (with `role="tooltip"`) to ensure proper accessibility.
