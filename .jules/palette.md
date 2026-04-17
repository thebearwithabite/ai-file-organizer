## 2024-03-16 - Make hover-only actions keyboard accessible
**Learning:** Actions hidden behind `opacity-0` and revealed with `group-hover:opacity-100` are completely inaccessible to keyboard-only users navigating via Tab. This is a common pattern for "secondary" actions like undo/delete buttons in lists.
**Action:** When using `opacity-0 group-hover:opacity-100` to hide secondary actions, always pair it with `focus-visible:opacity-100`, `focus-visible:ring-2`, and `focus-visible:outline-none` to ensure the action becomes visible and clearly highlighted when focused via keyboard navigation.

## 2024-04-17 - Extend keyboard accessibility to all hover-revealed elements
**Learning:** In addition to lists, interactive elements revealed only on hover within cards and library components (like copy buttons and upload actions) must also receive keyboard accessibility features. Otherwise, they remain invisible and unusable for screen reader and keyboard-only users.
**Action:** Apply `focus-visible:opacity-100`, `focus-visible:scale-100`, `focus-visible:translate-y-0`, `focus-visible:ring-2`, and `focus-visible:outline-none` (matching existing hover transitions) to all hidden actionable elements. Also add `aria-label`s to icon-only buttons.

## 2024-04-17 - Keyboard accessible liquid glass buttons
**Learning:** Visually hidden icon-only buttons (using `opacity-0 scale-90 group-hover:opacity-100 group-hover:scale-100`) are inaccessible to keyboard users and lack semantic meaning for screen readers.
**Action:** Pair hover visibility classes with explicit `focus-visible:opacity-100 focus-visible:scale-100` and standard focus rings (`focus-visible:ring-2 focus-visible:ring-background/50 focus-visible:outline-none`) alongside an `aria-label` to be fully keyboard accessible.
