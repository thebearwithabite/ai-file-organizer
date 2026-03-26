## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.

## 2024-03-26 - Make hover-only file inputs keyboard accessible
**Learning:** File inputs hidden with `className="hidden"` are completely inaccessible to screen readers and keyboard navigation, even when their `<label>` wrappers are visible. Hiding the label via `opacity-0 group-hover:opacity-100` compounds the issue for keyboard users.
**Action:** When creating hover-revealed file uploads, use `focus-within:opacity-100` on the label container. Ensure the `<input type="file">` is kept in the DOM as focusable but visually hidden using `opacity-0 absolute inset-0 w-full h-full cursor-pointer`.
