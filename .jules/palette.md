## 2024-03-17 - [Accessible hover-only elements]
**Learning:** Elements hidden via `opacity-0 group-hover:opacity-100` are inaccessible to keyboard navigation because they remain invisible on focus.
**Action:** Always add `focus-visible:opacity-100` along with explicit outline rings (`focus-visible:outline-none focus-visible:ring-2`) to ensure valid keyboard accessibility for hidden elements.
