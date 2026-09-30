// Site-wide settings for the web overlay (optional). Any key from the DEFAULTS block in overlay.html works here.
// Edit this on github.com (pencil icon) and commit; OBS picks it up after the site redeploys + a source refresh.
// NEVER put the Riot API key (or any password/token) in this file: everything here is public.
window.SITE_CONFIG = {
  channel: "calebgcameron",          // Twitch chat to read (anonymous, read-only)
  twitch: "twitch.tv/CalebGCameron",
  schedule: "Live Mon · Wed · Fri · Sat · 7:30pm Sydney time",
  x_handle: "@calebcameron_",
  tiktok: "@calebcameron_",
  youtube: "@lebthetapdancer",
  // Where rank.json / song.json are read from. "" = same site (GitHub Pages, recommended).
  // Netlify only: "https://raw.githubusercontent.com/YOUR-GITHUB-NAME/YOUR-REPO/main/"
  data: ""
};
