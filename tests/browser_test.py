"""Browser checks for the web overlay (optional; needs Playwright + Chrome). Not needed for streaming.
Serve the folder over HTTPS (or http) and pass the base URL, e.g.
    python tests/browser_test.py https://127.0.0.1:8443/trynd-overlay/
Checks: anonymous Twitch IRC join over wss, console errors, verse + socials, rank EXAMPLE chip,
song.json polling / ?song= / hide-when-empty, Restream iframe, make-scenes.html output."""
import asyncio, json, os, sys, urllib.parse
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://127.0.0.1:8443/trynd-overlay/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONG = os.path.join(ROOT, "song.json")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


async def new_page(b, errors):
    pg = await b.new_page()
    pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    return pg


async def main():
    orig_song = open(SONG, encoding="utf-8").read()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
        b = ctx
        # ---- 1. chat: anonymous Twitch IRC over wss from an https origin ----
        errs = []
        pg = await new_page(b, errs)
        sent, recv = [], []
        def on_ws(ws):
            ws.on("framesent", lambda f: sent.append(f if isinstance(f, str) else str(f)))
            ws.on("framereceived", lambda f: recv.append(f if isinstance(f, str) else str(f)))
        pg.on("websocket", on_ws)
        await pg.goto(BASE + "overlay.html?channel=calebgcameron&debug=1&fade=0")
        for _ in range(30):
            if await pg.evaluate("window.__overlay.joined"): break
            await pg.wait_for_timeout(500)
        st = json.loads(await pg.evaluate("JSON.stringify(window.__overlay)"))
        origin = await pg.evaluate("location.origin")
        joined_line = next((l for l in "\n".join(recv).split("\r\n") if " 366 " in l), "")
        check("page origin is https", origin.startswith("https://"), origin)
        check("Twitch IRC joined #calebgcameron anonymously",
              st.get("joined") and any(s.startswith("NICK justinfan") for s in sent)
              and any("PASS SCHMOOPIIE" in s for s in sent) and "#calebgcameron" in joined_line,
              f"status={st.get('status')} | {joined_line.strip()[:90]}")
        check("no OAuth token sent", not any("oauth:" in s.lower() for s in sent))
        await pg.wait_for_timeout(8000)
        n = await pg.evaluate("document.querySelectorAll('#chat .msg').length")
        print(f"     live chat messages rendered in 12s: {n} (0 is normal if the channel is offline/quiet)")
        rank_txt = await pg.inner_text("#rank")
        check("rank.json rendered with EXAMPLE chip", "EXAMPLE" in rank_txt and "DIAMOND IV" in rank_txt, rank_txt.replace("\n", " "))
        check("song strip hidden while song.json is empty", await pg.evaluate("document.getElementById('song').classList.contains('hidden')"))
        check("overlay.html: no console errors", not errs, "; ".join(errs)[:300])
        await pg.close()

        # ---- 2. queue scene: verse + socials + schedule, no console errors (incl. iframe) ----
        errs = []
        pg = await new_page(b, errs)
        await pg.goto(BASE + "queue.html?timer=1")
        await pg.wait_for_timeout(4000)
        fr = pg.frames[1]
        verse = (await fr.inner_text("#verse .vt p")).strip()
        ref = (await fr.inner_text("#verse .vref")).strip()
        socials = (await fr.inner_text("#socials")).replace("\n", " ")
        info = (await fr.inner_text("#info")).replace("\n", " ")
        check("verse of the day shows", len(verse) > 20 and ref and await fr.is_visible("#verse"), f"{ref}: {verse[:60]}...")
        check("socials show X/TikTok/YouTube", all(s in socials for s in ["@calebcameron_", "@lebthetapdancer"]) and socials.count("@calebcameron_") == 2, socials)
        check("schedule shows 7:30pm Sydney time", "7:30pm Sydney time" in info, info)
        for _ in range(20):
            if await fr.evaluate("window.__overlay.joined"): break
            await pg.wait_for_timeout(500)
        check("queue chat joined #calebgcameron", await fr.evaluate("window.__overlay.joined"))
        check("queue.html: no console errors", not errs, "; ".join(errs)[:300])
        await pg.close()

        # ---- 3. song: song.json polling, typo tolerance, ?song= override, empty hides ----
        errs = []
        try:
            pg = await new_page(b, errs)
            await pg.goto(BASE + "overlay.html?widgets=song&songpoll=5")
            await pg.wait_for_timeout(1500)
            hidden0 = await pg.evaluate("document.getElementById('song').classList.contains('hidden')")
            open(SONG, "w", encoding="utf-8").write('{\n  "song": "Test Artist - Test Title"\n}\n')
            await pg.wait_for_timeout(6500)
            t1 = await pg.inner_text("#song")
            check("song.json change appears after a poll", hidden0 and "Test Artist — Test Title" in t1, t1.strip())
            open(SONG, "w", encoding="utf-8").write('{ "song": "Broken, "oops" }')
            await pg.wait_for_timeout(6000)
            check("typo in song.json keeps the last song", "Test Artist" in await pg.inner_text("#song"))
            open(SONG, "w", encoding="utf-8").write('{"artist": "Artist B", "title": "Title B"}')
            await pg.wait_for_timeout(6000)
            check("artist/title form works", "Artist B — Title B" in await pg.inner_text("#song"))
            open(SONG, "w", encoding="utf-8").write(orig_song)
            await pg.wait_for_timeout(6000)
            check("empty song hides the strip again", await pg.evaluate("document.getElementById('song').classList.contains('hidden')"))
            await pg.goto(BASE + "overlay.html?widgets=song&song=" + urllib.parse.quote("URL Artist - URL Song"))
            await pg.wait_for_timeout(1000)
            check("?song= URL param shows fixed text", "URL Artist — URL Song" in await pg.inner_text("#song"))
            await pg.goto(BASE + "overlay.html?widgets=song&song=")
            await pg.wait_for_timeout(1000)
            check("empty ?song= hides the strip", await pg.evaluate("document.getElementById('song').classList.contains('hidden')"))
            errs = [e for e in errs if "song.json" not in e]  # the deliberate typo logs nothing, but be safe
            check("song tests: no console errors", not errs, "; ".join(errs)[:300])
            await pg.close()
        finally:
            open(SONG, "w", encoding="utf-8").write(orig_song)

        # ---- 4. Restream embed iframe from https ----
        errs = []
        pg = await new_page(b, errs)
        rs = urllib.parse.quote("https://chat.restream.io/embed?token=00000000-test-token", safe="")
        await pg.goto(BASE + f"overlay.html?widgets=chat&chat=restream&restream_url={rs}")
        await pg.wait_for_timeout(6000)
        fr_urls = [f.url for f in pg.frames]
        blocked = [e for e in errs if "frame" in e.lower() and ("refused" in e.lower() or "ancestors" in e.lower())]
        status = await pg.evaluate("window.__overlay.status")
        check("Restream iframe loads from https (not frame-blocked, no mixed content)",
              any("restream.io" in u for u in fr_urls) and status == "restream-loaded" and not blocked and not any("Mixed Content" in e for e in errs),
              f"status={status}; frames={[u[:60] for u in fr_urls]}")
        print("     (console lines from inside Restream's own page with a fake token are ignored:", len(errs), ")")
        await pg.close()

        # ---- 5. make-scenes.html rewrites the base URL ----
        errs = []
        pg = await new_page(b, errs)
        await pg.goto(BASE + "tools/make-scenes.html")
        prefill = await pg.input_value("#base")
        await pg.fill("#base", "calebcameron.github.io/trynd-overlay")
        async with pg.expect_download() as dl:
            await pg.click("#dl")
        d = await dl.value
        path = "/tmp/make-scenes-download.json"
        await d.save_as(path)
        data = json.load(open(path))
        urls = [s["settings"]["url"] for s in data["sources"] if s["id"] == "browser_source"]
        check("make-scenes pre-fills the site address when hosted", prefill == BASE, prefill)
        check("make-scenes download has real base URL, no placeholder",
              urls == ["https://calebcameron.github.io/trynd-overlay/overlay.html?channel=calebgcameron",
                       "https://calebcameron.github.io/trynd-overlay/queue.html?timer=1"] and "YOUR-SITE" not in open(path).read(), urls)
        check("scene file keeps Game + Queue scenes", [x["name"] for x in data["scene_order"]] == ["Game", "Queue"])
        await pg.select_option("#chat", "restream")
        await pg.fill("#rs", "https://chat.restream.io/embed?token=abc")
        await pg.select_option("#status", "champ")
        txt = await pg.inner_text("#urls")
        check("make-scenes restream/status options", "chat=restream" in txt and "status=champ" in txt and "token=abc" not in txt, txt.replace("\n", " ")[:160])
        check("make-scenes: no console errors", not errs, "; ".join(errs)[:300])
        await pg.goto(BASE + "index.html"); await pg.wait_for_timeout(800)
        check("index.html: no console errors", not errs, "; ".join(errs)[:300])
        await pg.close()
        await ctx.close()
    print(f"\n{sum(ok for _, ok in results)}/{len(results)} checks passed")
    return 0 if all(ok for _, ok in results) else 1

sys.exit(asyncio.run(main()))
