// Site-wide settings for the web overlay (optional). Any key from the DEFAULTS block in overlay.html works here.
// Edit this on github.com (pencil icon) and commit; OBS picks it up after the site redeploys + a source refresh.
// NEVER put the Riot API key (or any password/token) in this file: everything here is public.
window.SITE_CONFIG = {
  channel: "calebgcameron",          // Twitch chat to read (anonymous, read-only)
  twitch: "twitch.tv/CalebGCameron",
  schedule: "Live Tue · Wed · Thu · Fri · Sat · 12pm Sydney time",
  x_handle: "@calebcameron_",
  tiktok: "@calebcameron_",
  youtube: "@lebthetapdancer",
  // Champion icon + mastery (rank card; the queue scene also shows a mastery strip under it)
  champ: "Tryndamere",
  champ_icon: "assets/trynd-emblem.svg",  // stylised emblem. Or "assets/trynd-emblem-blade.svg", "assets/tryndamere.png" (Riot portrait), "" = old gem emblem
  mastery: "2,600,000+",                // change the number here whenever you like
  mastery_label: "Mastery",
  mastery_show: 1,                      // 0 = hide the mastery line/strip
  // The journey line. Style: 1 = tier ladder ("you are here" = tier from rank.json), 2 = steel plaque, 3 = minimal tag line
  journey_show: 1,                      // 0 = hide it
  journey_style: 1,
  journey_from: "Bronze 5",
  journey_to: "Challenger",
  journey_title: "The 12 Year Journey",
  // Where rank.json / song.json are read from. "" = same site (GitHub Pages, recommended).
  // Netlify only: "https://raw.githubusercontent.com/YOUR-GITHUB-NAME/YOUR-REPO/main/"
  data: ""
};
