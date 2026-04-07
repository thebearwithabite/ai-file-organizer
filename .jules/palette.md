## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.
## 2024-04-07 - Accessible File Uploads inside Hover Containers
**Learning:** In Tailwind, replacing `hidden` with `sr-only` or `opacity-0 absolute inset-0` on file inputs makes them focusable for keyboard users. To make their hover-only parent containers visibly appear when the hidden input receives focus, apply `focus-within:opacity-100` to the parent container.
**Action:** Whenever creating hover-only file upload buttons, always ensure the input is visually hidden rather than `display: none` and pair it with `focus-within` classes on its container to guarantee keyboard accessibility.
