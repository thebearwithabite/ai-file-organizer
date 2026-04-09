## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.
## 2024-05-24 - Navigation Link Accessibility
**Learning:** Custom navigation links built with React Router's `<Link>` or `<NavLink>` often lack semantic indication of the active page for screen readers, and rely heavily on visual cues. They also miss explicit focus rings unless styled manually.
**Action:** Always add `aria-current="page"` to the active navigation item and explicitly define `focus-visible` styles on custom link wrappers to ensure keyboard and screen reader accessibility. Add `aria-hidden="true"` to decorative icons within links to prevent redundant announcements.
