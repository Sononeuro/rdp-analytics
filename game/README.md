# Bellwether: Cre-8 Chronicles

A 2D creature-collection RPG built as a Progressive Web App. Single URL,
installable, offline-capable after first load.

> Status: **Phase 1 — scaffold.** A blue Phaser scene loads at `/`, the service
> worker registers, the manifest validates. No gameplay yet. See `PHASES.md` for
> the full roadmap and what each phase delivers.

## Stack

- [Phaser 3.80+](https://phaser.io) on TypeScript 5 (strict)
- [Vite](https://vitejs.dev) for dev/build
- [vite-plugin-pwa](https://vite-pwa-org.netlify.app/) (Workbox) for the service
  worker, manifest, offline cache, and update prompt
- [Howler.js](https://howlerjs.com) for audio _(added in a later phase)_
- [Zustand](https://zustand-demo.pmnd.rs/) for global game state _(later phase)_
- [Dexie](https://dexie.org/) for IndexedDB save persistence _(later phase)_
- ESLint + Prettier strict
- [Vitest](https://vitest.dev) for unit tests
- Deploys to Vercel via `vercel.json` at the repo root

## Develop

```bash
cd game
npm install
npm run dev          # http://localhost:5173
```

Other scripts:

```bash
npm run typecheck    # tsc --noEmit
npm run lint         # eslint
npm run test         # vitest run
npm run build        # production build into ./dist
npm run preview      # serve the built bundle
npm run generate:icons   # rebuild placeholder PWA icons from public/favicon.svg
```

The dev server runs on `http://localhost:5173`. Service worker registration is
disabled in dev (vite-plugin-pwa default) so hot reload behaves; build & preview
to test the SW path.

## Layout

```
game/
  src/
    scenes/    Boot, Preload, Title, Overworld, Battle, Menu, Dialog, FieldGuide
    systems/   battle, encounter, capture, save, dialog, audio, input, evolution, progression
    data/      creatures, moves, types, items, npcs, dialog, regions, learnsets
    entities/  Player, NPC, Cre8, Trainer
    ui/        HUD, BattleUI, MenuUI, DialogBox, VirtualJoystick, ActionWheel, …
    state/     Zustand stores
    pwa/       service-worker registration + update prompt
    assets/    sprites, tilemaps, audio, fonts
  tests/       vitest specs for systems and data
  public/      icons, splash, favicon
  scripts/     icon generator and other build helpers
```

## Deploy

`vercel.json` lives at the repository root and builds from `game/`. Connect the
repo on Vercel; preview deploys are produced for every push to a non-main
branch.

## Quality bar (per-phase target)

- Strict TypeScript, no `any`
- 80%+ unit-test coverage on `src/systems/**` and `src/data/**`
- No console errors in normal play
- Lighthouse: PWA 100, Performance 90+, Accessibility 95+

## Project notes

- **iOS Safari:** `100dvh` instead of `vh`, safe-area insets on the canvas
  wrapper, audio context unlocked on first touch _(in later phase)_, no
  `localStorage` (IndexedDB only).
- **No legacy code.** Everything in `game/` is fresh for this project.
- **Asset placeholders:** Cre-8 sprites are programmatic 64×64 silhouettes
  derived from species type/BST until real art lands. Search the codebase for
  `TODO(art)` to find swap-in points.

See `CREDITS.md` for third-party attribution.
