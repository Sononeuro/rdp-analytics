# Roadmap

Phased delivery. Each phase is independently playable; we stop, deploy a Vercel
preview, and wait for confirmation before starting the next.

| Phase | Deliverable                                                                              | Status         |
| ----- | ---------------------------------------------------------------------------------------- | -------------- |
| 1     | Vite + Phaser + TS scaffold, blue scene at `/`, SW registers, manifest validates, Vercel | **in progress** |
| 2     | Type chart, creature data model, move data model, IVs, evolution data + unit tests       | pending        |
| 3     | Pure-logic BattleEngine: ATB, cooldowns, damage formula, type effectiveness, statuses    | pending        |
| 4     | Battle scene with action wheel + keyboard hotkeys, ATB gauges, damage numbers            | pending        |
| 5     | Overworld scene, Tiled loader, joystick + WASD + click-to-move, collision, NPCs          | pending        |
| 6     | Dialog system, NPCs, scripted scenes, Region 1 fully populated                           | pending        |
| 7     | Encounter triggers, battle transitions, overworld state preservation                     | pending        |
| 8     | Capture system: Pulse Tag tiers, charge gauge, vibration, capture math                   | pending        |
| 9     | Party / box / inventory / shops / healing centers / IndexedDB save with migrations       | pending        |
| 10    | XP, leveling, move-learn prompt, evolution sequence (cancellable), Field Guide           | pending        |
| 11    | Regions 2–5: maps, NPCs, encounters, boss battles, story beats                           | pending        |
| 12    | Polish: audio, particles, accessibility audit, install prompt UI, perf, Lighthouse       | pending        |
