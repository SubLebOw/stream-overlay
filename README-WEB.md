# Trynd OTP Overlay: web version (stream from any PC, nothing to install)

This is your overlay pack as a **website**. OBS loads it by URL, so a cafe PC needs nothing installed
except OBS: no Python, no .bat files, no Tuna, no files to keep. Everything that changes (rank, song) lives online.

- **Chat**: Twitch chat for **calebgcameron**, read anonymously. No login, and nothing is posted. You can switch to Restream's combined chat instead.
- **Rank**: GitHub updates it for you about every 15 minutes, using your Riot key kept as a secret.
- **Song**: you type it into one small file (`song.json`) on github.com from your phone.
- **Queue scene**: title and timer, rank, song, Twitch and schedule card (7:30pm Sydney time), socials (X / TikTok @calebcameron_, YouTube @lebthetapdancer), verse of the day, and big chat.

Your original local pack (`trynd-overlay/`) is unchanged and still works at home.

| File | What it is |
|---|---|
| `index.html` | Home page of the site, with your OBS URLs and a link to the song editor |
| `overlay.html`, `queue.html`, `verses.js` | The overlay itself (same look as the local pack) |
| `site-config.js` | Site-wide settings: channel, schedule, socials. Public, so **never put keys or passwords here** |
| `rank.json` | Rank shown on stream. **It's a PLACEHOLDER (marked EXAMPLE) until the Riot updater runs.** |
| `song.json` | The song text you edit from your phone |
| `scripts/update_rank.py` | The rank updater that GitHub runs (Riot API → `rank.json`) |
| `.github/workflows/update-rank.yml` | Runs the updater about every 15 min and saves `rank.json` if it changed |
| `.github/workflows/deploy-pages.yml` | Publishes the site to GitHub Pages whenever something changes |
| `obs/trynd-web-scenes.json` | OBS scene collection (Game + Queue scenes). Uses the placeholder `https://YOUR-SITE/` |
| `obs/OBS-NOTES.md` | What's in the scene file, plus game-capture tips |
| `tools/make-scenes.html` | Puts your real site address into the scene file. **One step.** |
| `tools/make-url.html` | Builds a single Browser Source URL (Restream chat, fixed song, etc.) |
| `netlify.toml` | Only used if you host on Netlify instead of GitHub Pages |
| `tests/` | Offline tests for the updater (mocked Riot answers) and a browser check. Not needed for streaming. |
| `previews/` | Screenshots of the overlay |

---

## A. One-time setup: put the site online with GitHub Pages (recommended, free)

Do this once, at home or on any PC. It takes about 10 minutes, and it all happens in the browser on github.com.

1. **Sign in to github.com** with your own account, or make a free one. Only you type your password.
2. Click **+ → New repository**.
   - Name: `trynd-overlay`
   - Choose **Public**. Free GitHub Pages needs a public repo. Nothing secret is in these files: the Riot key goes into a *secret*, not a file.
   - Leave "Add a README" unticked. Click **Create repository**.
3. On the empty repo page, click **uploading an existing file**. Unzip `trynd-overlay-web.zip` on your PC, open the
   `trynd-overlay-web` folder, select **everything inside it** (including the `.github` folder), and drag it onto the page.
   Click **Commit changes**.
   - Check that the repo now shows a `.github` folder. If it's missing (some computers hide folders starting with a dot):
     click **Add file → Create new file**, type the name `.github/workflows/update-rank.yml`, paste in that file's contents
     from the zip, and commit. Do the same for `.github/workflows/deploy-pages.yml`.
4. Go to **Settings → Pages**. Under *Build and deployment → Source*, choose **GitHub Actions**.
5. Go to the **Actions** tab, click **Deploy site to GitHub Pages**, then **Run workflow → Run workflow**. Wait for the green tick (about 1 minute).
6. Your site is now at **`https://YOUR-GITHUB-NAME.github.io/trynd-overlay/`**. Open it. The home page shows your
   exact OBS URLs and a **"Open the song.json editor"** link. Bookmark both on your phone.
7. Make the OBS file: open **`https://YOUR-GITHUB-NAME.github.io/trynd-overlay/tools/make-scenes.html`**. It fills in
   your address for you. Click **Download scene file**. Save the `.json` to a **USB stick** and/or your **Google Drive**.
   (You can also just open this page at the cafe and download it there.)

From now on, the site updates itself whenever you edit a file on GitHub or the rank changes. Each update takes about 1 minute to go live.

### Alternative: Netlify

Use this only if you can't use GitHub Pages. The GitHub repo is still needed, because the rank updater runs there.

1. Do steps 1–3 above.
2. Sign in at **app.netlify.com** (the "Sign in with GitHub" option is easiest). Click **Add new project → Import an existing project → GitHub**, then pick `trynd-overlay`.
   Leave the build command empty, set the publish directory to `.`, and click **Deploy**. If Netlify says the project is *private*, **publish** it; OBS can't load a private site.
3. Netlify's free plan only includes about **20 deploys a month** (300 credits, 15 per deploy). So rank and song changes are *not*
   deployed; `netlify.toml` skips them. Instead, the overlay reads them straight from GitHub. On github.com, edit `site-config.js` and set:
   `data: "https://raw.githubusercontent.com/YOUR-GITHUB-NAME/trynd-overlay/main/"`
   GitHub's raw files are cached for up to about 5 minutes, so a song change can take up to 5 minutes to show on Netlify.
4. Delete `.github/workflows/deploy-pages.yml` in the repo, since it's only for GitHub Pages.
5. Your site is `https://SOMETHING.netlify.app/`. Use that in make-scenes.html.

---

## B. Turn on the real rank (Riot API key as a GitHub secret)

Until you do this, the rank card shows the placeholder **DIAMOND IV · 0 LP** with a yellow **EXAMPLE** tag. That's not your real rank.

1. Go to **developer.riotgames.com** and log in with your Riot account.
   - The key on the dashboard is a **Development key. It expires every 24 hours**, so it's fine for testing but you'd have to replace it daily.
   - For always-on rank, click **Register Product → Personal API Key**. Describe it honestly, for example: "Stream overlay that shows my own
     League rank (Caleb Cameron#ccxx, OCE)". Riot reviews these, which can take a while. Personal keys don't expire daily.
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `RIOT_API_KEY`
   - Secret: paste the key (`RGAPI-…`). Click **Add secret**.
3. Test it: **Actions → Update rank → Run workflow**. When it goes green, `rank.json` shows your real rank and the EXAMPLE tag disappears
   after the site redeploys (about 1 minute).
4. When the key changes (a new dev key, or your Personal key arrives), go to the same page, click **RIOT_API_KEY → Update**, and paste the new key.

How it works: every ~15 minutes GitHub runs `scripts/update_rank.py`. It looks up **Caleb Cameron#ccxx** (account-v1 on `asia`)
and reads Ranked Solo/Duo from **OCE (`oc1`)**, league-v4. It saves `rank.json` only if something changed, then republishes the site.
"Today W/L" counts from the first check after **midnight Sydney time**. The key exists only inside GitHub's runner and is
never written into the website. OBS and viewers only ever see the finished `rank.json`.

- A red or yellow note in the Actions tab saying "key missing, invalid or expired" means it's time to update the secret. Your last rank stays on screen.
- GitHub sometimes starts scheduled runs a few minutes late. That's normal.
- If the repo has no activity for 60 days, GitHub pauses scheduled workflows and emails you. Re-enable it in the Actions tab.
- Manual override: edit `rank.json` on github.com. Set `"example": false` to hide the tag. The next automatic run replaces it again, as long as a key is set.

---

## C. At the internet cafe (about 2 minutes)

**Before you go:** have the scene file on a USB stick or in Google Drive. Or skip that and open
`https://YOUR-GITHUB-NAME.github.io/trynd-overlay/tools/make-scenes.html` at the cafe and click **Download**.

1. **Open OBS** (it has to be installed on the cafe PC).
2. **Get the scene file.** Plug in the USB, or open Google Drive in the browser and download the `.json`. On a shared PC, use a private/incognito window.
3. **Import it:** in OBS, click **Scene Collection → Import**, then **…**, pick the file, make sure it's ticked, and click **Import**.
   Then open **Scene Collection → Trynd Web Overlay** to switch to it.
4. **Video:** in **Settings → Video**, set Base (Canvas) to **1920x1080**. Pick an output of 1920x1080, or 1280x720 on a weak PC.
5. **Log into Restream:** in **Settings → Stream**, set Service to **Restream.io** and click **Connect Account**. Log in yourself in the window that opens.
   If Connect Account isn't there, choose **Use Stream Key** and paste the key from restream.io (in a private window).
6. **Check the Game scene:** League should show. If it's black, hide **Game Capture** and show **Display Capture** (double-click it and pick the screen).
   See `obs/OBS-NOTES.md`.
7. Click **Start Streaming**. Send a test message in your Twitch chat from your phone. It should pop up on the overlay.

**Staying safe on a shared PC**
- Type your passwords yourself. **Never share them** with staff, friends or chat. Click **"Never"** when a browser offers to save a password.
- Use two-factor login (phone app or SMS) on Riot, GitHub, Restream and Google.
- When you finish: **Stop Streaming**, go to **Settings → Stream → Disconnect Account**, sign out of Google Drive and Restream in the browser, and close it.
  Cafe PCs usually wipe on logout, but don't rely on that.
- The Riot key never goes near the cafe PC. It lives only in GitHub.

---

## D. Change the song from your phone

1. On your phone, open the **song.json editor** bookmark:
   `https://github.com/YOUR-GITHUB-NAME/trynd-overlay/edit/main/song.json`
   (you'll need to be signed in to github.com in your phone browser). Or open the repo, tap `song.json`, then tap the pencil (✏️) or the **…** menu → **Edit**.
2. Change only the text between the quotes:
   ```json
   {
     "song": "Artist - Title"
   }
   ```
3. Tap **Commit changes… → Commit changes**, choosing "commit directly to main".
4. It appears on stream in **about 1–2 minutes**: the site republishes in about 1 minute, and the overlay checks every 30 seconds.
5. To **hide** the song strip, make it empty: `"song": ""`.

- If you accidentally break the file (for example, a missing quote), the overlay keeps showing the last song until you fix it.
- `{"artist": "…", "title": "…"}` also works.
- **Fixed song for a whole stream:** add `&song=Artist%20-%20Title` to the overlay URL in OBS. An empty `&song=` hides the strip.
- **Music rights:** only play music you're allowed to stream. Twitch acts on DMCA claims, and a normal Spotify plan doesn't cover streaming.
  Stream-safe options include StreamBeats (free), Pretzel and Epidemic Sound. Check their terms.

---

## E. Chat options

- **Twitch (default):** chat is read anonymously over a secure connection (`wss://irc-ws.chat.twitch.tv`). It doesn't need a login and never posts.
  It shows new messages from the moment the source loads. Add `&debug=1` to the URL to see "joined #calebgcameron".
- **Restream combined chat (Twitch + YouTube + …):** on restream.io, open **Chat → Embed in stream**, choose "Embed chat from any live stream",
  set the background opacity to 0, and copy the URL. In **make-scenes.html** (or make-url.html), choose *Restream combined chat* and paste it.
  **Treat that URL like a password.** It ends up in your OBS scene file, so keep that file private. Never put it in the GitHub repo.
  If the embedded chat misbehaves, use the "frame only" fallback from the original README: `chat=restream` without `restream_url`, with
  Restream's URL as its own Browser Source at x 1490, y 181, 410×449 (in-game) or x 1360, y 87, 500×937 (queue).

## F. Settings you can add to a URL

These are the same as the local pack (`font`, `max`, `fade`, `opacity`, `x,y,w,h`, `rankx/ranky`, `songx/songy`, `scale`, `widgets`,
`hidebots`, `hidecmds`, `badges`, `status`, `timer`, `title`, `subtitle`, `scenebg`, `cam`, `verse`, `verse_ref`, `demo`, `debug`). Also:

| Setting | What it does |
|---|---|
| `song` | Fixed song text; empty hides the strip. When set, song.json is ignored |
| `songpoll` / `rankpoll` | Seconds between checks (default 30 / 60) |
| `data` | Where rank.json/song.json come from (usually set in site-config.js; only for Netlify) |
| `champ` / `champ_icon` | Champion name and square portrait on the rank card (default `Tryndamere`, `assets/tryndamere.png`; empty `champ_icon` = old gem emblem) |
| `mastery` / `mastery_label` | Mastery text, e.g. `2,000,000+` and `Mastery` (in-game: a line inside the rank card; queue: a strip under the rank card) |
| `mastery_show` | `0` hides the mastery line/strip |
| `masteryx` / `masteryy` | Queue scene: position of the mastery strip (default 760, 394) |

To change the socials, schedule or mastery number for the whole site, edit `site-config.js` on github.com.
The Tryndamere portrait is Riot's Data Dragon square icon (patch 16.19.1), stored in `assets/` so nothing loads from Riot at stream time.

## G. Restream Studio (streaming from the browser, no OBS)

Restream Studio now has a **Browser Source** widget (Widgets → Add → paste a URL). You could try `overlay.html` there.
**This is untested**, so check the following before relying on it: whether Studio keeps the page transparent, whether it scales a 1920×1080 page to the canvas,
and whether it fits within the free plan's limit of 1 widget per scene. The queue timer's "restart when the scene goes live" only works in OBS.
Studio's own Graphics → Overlays only take images and videos, which can't show live chat or rank.

## Troubleshooting

- **Blank overlay:** open the same URL in a normal browser. If it works there, right-click the source in OBS → **Refresh**.
- **Rank still says EXAMPLE:** check that the `RIOT_API_KEY` secret is set, then look at Actions → Update rank for a warning.
- **Song didn't change:** check that Actions → Deploy site shows a green tick for your edit, then wait 30 seconds.
- **Chat empty:** it only shows messages sent after the source loaded. Try `&debug=1`.
