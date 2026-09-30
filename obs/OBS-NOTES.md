# OBS scene collection: `trynd-web-scenes.json`

A portable OBS scene collection with two scenes. Import it with **Scene Collection → Import**.

The URLs inside point at the placeholder **`https://YOUR-SITE/`**. Don't edit the JSON by hand. Open
**`tools/make-scenes.html`** (on your site, or double-click it from a USB stick), type your site address,
and click **Download**. That gives you a ready-to-import file with the real URL.

**Ready-made for this site:** `obs/caleb-obs-scenes.json` already points at `https://sublebow.github.io/stream-overlay/`
(Twitch chat, IN QUEUE title with timer). Import it directly.

## What's inside

| Scene | Sources (top of the list = drawn on top) | Notes |
|---|---|---|
| **Game** | `Trynd Overlay (chat + rank + song)`: Browser, 1920×1080, `overlay.html?channel=calebgcameron` (locked) | Chat on the right, rank and song top-left |
| | `Game Capture (League of Legends)`: window `League of Legends.exe`, anti-cheat hook on, scaled to fit 1920×1080 | Captures only the game window |
| | `Display Capture (fallback - turn on if Game Capture is black)`: **hidden** | For cafe PCs where Game Capture won't hook |
| **Queue** | `Trynd Queue Scene`: Browser, 1920×1080, `queue.html?timer=1` (locked) | Title + timer, rank, song, verse, socials, chat |
| | `Webcam (optional)`: Video Capture Device at x 80, y 222, fitted to 640×360 | Sits *behind* the frame's transparent hole |

It also includes Desktop Audio and Mic/Aux, both set to the Windows default devices.
Browser sources have **"Shutdown source when not visible"** off, so chat stays connected. They use OBS's default transparent CSS.

## After importing (about 30 seconds)

1. Open the **Scene Collection** menu and click **Trynd Web Overlay**. Importing adds the collection but doesn't switch to it.
2. Go to **Settings → Video** and set **Base (Canvas) Resolution to 1920x1080**. The overlay is laid out for 1080p. Output can be 1280x720 if the PC is weak.
3. **Game Capture:** start a game or practice tool. If the preview shows League, you're done.
   - If it's **black**, which is common on cafe PCs (anti-cheat, locked-down Windows, multi-GPU laptops):
     click the eye to hide **Game Capture**, click the eye to show **Display Capture**, then double-click it and
     pick the monitor League is on. Display Capture shows everything on that screen, so close other windows.
   - Run League in **Borderless** or **Windowed** mode if Game Capture has trouble with fullscreen.
   - If Game Capture shows the wrong window: double-click it, set Mode to *Capture specific window*, and pick
     `[League of Legends.exe]: League of Legends (TM) Client`.
4. **Webcam** (Queue scene): double-click **Webcam (optional)** and pick the camera. With no camera, the frame just stays empty.
5. **Other queue states:** right-click the Queue scene, choose **Duplicate**, then edit the browser source URL to
   `queue.html?status=champ&timer=1` (or `status=back`, `status=starting`). You can also pick the status in make-scenes.html.

## Format

The format follows OBS Studio 30.x scene-collection JSON (`prev_ver` 503447555 = libobs 30.2.3). It has
`current_scene`, `scene_order`, `sources` (scenes store their items with `source_uuid`), `groups`, `quick_transitions`,
`transitions`, and the audio devices as top-level `DesktopAudioDevice1` / `AuxAudioDevice1`. This matches the fields OBS 30 itself
saves. It also has the three keys OBS's importer checks for (`sources`, `name`, `current_scene`).
It was built from OBS's source code but hasn't been imported into a real copy of OBS yet. Do one test import at home first.
Game Capture, Display Capture, Webcam and the audio sources are Windows source types. On a Mac they're converted or skipped.
To rebuild it after editing `scripts/build_obs_scenes.py`, run `python scripts/build_obs_scenes.py`.
That also refreshes the copy embedded in `tools/make-scenes.html`.
