# InkSpeed

A typing trainer with three game modes, personal bests, a leaderboard, custom
challenge passages, and achievements. Everything runs in the browser — scores
are saved in your own browser's local storage (key `inkspeed-db-v1`), so no
server or database is needed to try it.

## Run it locally

You need Node.js (LTS). From the folder that contains `package.json`:

```sh
npm install
npm run dev
```

Then open the URL the terminal prints (usually `http://localhost:5173`).

Other useful commands:

```sh
npm run build      # production build
npm run test       # run the rule checks (vitest)
npm run lint       # eslint
```

If you use Bun instead of npm, `bun install` / `bun run dev` work too.

## Game modes

| Mode | Durations | Score |
| --- | --- | --- |
| Classic | 60s / 180s / 300s | words per minute × accuracy |
| Memory Rush | 15s / 30s / 60s | rounds passed (a round needs 90% accuracy, one miss ends the run) |
| Key Chaos | 15s / 30s / 60s | like Classic, but some letter keys are swapped |

Key Chaos scrambling scales with difficulty: **Easy** swaps 5 letter keys,
**Medium** 8, **Hard** 10, and **Any** picks one of those at random. Only the
swapped keys appear in the "to type ↑ press ↓" legend.

## Screens

- `/` — add, rename, select and delete players; pick a mode
- `/play/$mode` — the game itself (setup → memorize → typing → results)
- `/history` — personal bests and past results
- `/leaderboard` — best score per player, per mode
- `/challenges` — write, edit and delete your own passages (10–400 characters)
- `/achievements` — the six achievements, locked or unlocked, with unlock dates

## Where the rules live

All scoring, accuracy, personal-best and achievement logic sits in
`src/lib/inkspeed.ts`, covered by `src/lib/inkspeed.test.ts`.

## Built with

- TanStack Start (React 19 + Vite)
- TypeScript
- Tailwind CSS v4
- Vitest
