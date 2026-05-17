# Frontend Architecture

## Structure
- `pages/`: route-level screens.
- `layouts/`: app shell/navigation.
- `components/`: reusable UI units.
- `services/`: API adapters.
- `hooks/`: stateful view logic.
- `styles/`: global and shared style primitives.

## Guidance
- Keep protocol/UI logic in page-level containers.
- Promote repeated controls to shared components.
