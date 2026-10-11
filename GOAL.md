# Starlink donation goal bar

The overlay shows a **STARLINK GOAL** bar in the slot where the Tryndamere mastery used to be:

- **Game overlay** (`overlay.html`): a row inside the rank card (top-left), replacing the mastery row.
- **Queue scene** (`queue.html`): the strip under the rank card in the right column (1136, 398), replacing the mastery strip.

It reads `goal.json` every 30 seconds:

```json
{ "title": "STARLINK GOAL", "raised": 0, "goal": 1000, "currency": "NZD", "show": true }
```

## Update the total (phone is fine)

1. Open `https://github.com/SubLebOw/stream-overlay/edit/main/goal.json`.
2. Change `"raised"` to the new total (just the number, e.g. `"raised": 145`). Commit.
3. The site redeploys in about a minute; the bar animates up with a "+$" pop and sparks. At 100% it turns gold.

- `"show": false` hides the bar and brings the mastery strip/row back.
- A typo in goal.json is ignored (the last good value stays on screen).

## URL options

| Param | What it does |
|---|---|
| `goal=0` | Hide the goal bar on this source (mastery comes back) |
| `goalfile=other.json` | Read a different file |
| `goalpoll=30` | Seconds between checks (min 10) |
| `goalx`, `goaly`, `goalw` | Move/resize it (queue scene only) |

## Later: automatic totals from StreamElements (not set up)

Do not put any token in the website: everything in this repo is public. The safe way is the same pattern as the Riot rank updater:

1. Add a repo secret `SE_JWT` (StreamElements dashboard → Account → Channels → Show secrets → JWT token) and a variable `SE_CHANNEL_ID`.
2. A workflow (`update-goal.yml`, every 15 min) calls `GET https://api.streamelements.com/kappa/v2/tips/{SE_CHANNEL_ID}?after=<goal start>&limit=100` with `Authorization: Bearer $SE_JWT`, sums the NZD tips since the goal started, writes `raised` into goal.json, and commits only if it changed (then triggers the Pages deploy, like update-rank.yml).
3. Kick subs/KICKs and Twitch bits don't go through StreamElements tips, so either add them by hand (`"raised_extra"`) or leave the bar as "tips only".
