#!/usr/bin/env python3
"""Rebuilds ../verses.js by FETCHING each verse from bible-api.com (World English Bible, public domain).
Usage: python tools/build_verses.py      (takes ~8 min: bible-api.com allows ~15 requests / 30 s)
Edit REFS below to add/remove verses."""
import json, os, re, time, urllib.parse, urllib.request, urllib.error

REFS = {
 "strength": ["Isaiah 40:31","Isaiah 41:10","Philippians 4:13","Psalm 46:1","Psalm 28:7","Nehemiah 8:10","2 Corinthians 12:9","Psalm 73:26",
   "Ephesians 6:10","Isaiah 40:29","Habakkuk 3:19","Psalm 18:32","Exodus 15:2","Psalm 121:1-2","2 Timothy 1:7","Joshua 1:9","Deuteronomy 31:6",
   "Psalm 27:1","Psalm 31:24","1 Chronicles 16:11","1 Corinthians 16:13"],
 "perseverance": ["James 1:12","Romans 5:3-4","Galatians 6:9","Hebrews 12:1","Hebrews 10:36","James 1:2-4","2 Timothy 4:7","Philippians 3:13-14",
   "1 Corinthians 15:58","Romans 12:12","2 Thessalonians 3:13","2 Corinthians 4:16-18","2 Corinthians 4:8-9","1 Peter 5:10","Philippians 1:6","Romans 8:18"],
 "discipline": ["1 Corinthians 9:24-27","Proverbs 25:28","Titus 2:11-12","Proverbs 12:1","1 Timothy 4:8","Proverbs 13:4","Proverbs 21:5","Colossians 3:23",
   "Proverbs 16:32","Galatians 5:22-23","2 Peter 1:5-7","Proverbs 6:6-8","Proverbs 14:23","Ecclesiastes 9:10","1 Corinthians 10:13","Hebrews 12:11","2 Timothy 2:15"],
 "humility": ["Philippians 2:3-4","James 4:10","1 Peter 5:6-7","Micah 6:8","Proverbs 11:2","Proverbs 16:18","Proverbs 22:4","Matthew 23:12","Colossians 3:12",
   "Ephesians 4:2","Romans 12:3","Proverbs 27:2","James 4:6","Matthew 5:5","Mark 10:45","1 Samuel 16:7"],
 "peace": ["John 14:27","Philippians 4:6-7","Isaiah 26:3","Psalm 4:8","Colossians 3:15","Romans 12:18","Matthew 5:9","John 16:33","Numbers 6:24-26",
   "Psalm 29:11","Romans 15:13","2 Thessalonians 3:16","Psalm 34:14","Isaiah 32:17","Matthew 11:28-30","Psalm 46:10"],
 "gratitude": ["1 Thessalonians 5:16-18","Psalm 107:1","Psalm 100:4-5","Colossians 3:17","Psalm 118:24","Psalm 136:1","James 1:17","Psalm 9:1",
   "Ephesians 5:20","Psalm 103:2","Colossians 4:2","Psalm 95:2","Psalm 126:3","Philippians 4:11-12"],
 "grace": ["Ephesians 2:8-9","2 Corinthians 9:8","Hebrews 4:16","Titus 3:5","Romans 3:23-24","John 1:16","Romans 5:8","Lamentations 3:22-23",
   "2 Corinthians 5:17","Romans 8:1","1 John 1:9","Psalm 103:12","Micah 7:18","Isaiah 1:18","Ephesians 4:32","Galatians 2:20"],
 "wisdom": ["James 1:5","Proverbs 3:5-6","Proverbs 1:7","Proverbs 4:7","Proverbs 2:6","Proverbs 9:10","Proverbs 15:1","Proverbs 18:13","Proverbs 19:20",
   "Proverbs 27:17","Proverbs 16:3","Proverbs 16:9","James 3:17","Ecclesiastes 3:1","Psalm 90:12","Proverbs 12:15","Proverbs 17:22","Proverbs 4:23",
   "Colossians 4:6","James 1:19-20","Ephesians 4:29","Proverbs 10:19","Romans 12:2","James 1:22","Psalm 119:105","Ecclesiastes 4:9-10"],
 "patience": ["Psalm 27:14","Psalm 37:7","Lamentations 3:25-26","Ecclesiastes 7:8","Romans 8:25","Isaiah 30:18","Psalm 40:1","Micah 7:7","Habakkuk 2:3","James 5:7-8"],
 "love": ["1 Corinthians 13:4-7","John 3:16","1 John 4:7-8","1 John 4:18","1 John 4:19","Romans 8:38-39","John 15:13","John 13:34-35","1 Corinthians 16:14",
   "Colossians 3:14","1 Peter 4:8","Romans 13:10","Zephaniah 3:17","Mark 12:30-31","Galatians 5:13","1 John 3:18","Romans 12:9-10","Proverbs 17:17","Ruth 1:16"],
 "hope": ["Jeremiah 29:11","Romans 15:4","Hebrews 11:1","Psalm 42:11","Romans 8:28","Psalm 39:7","Proverbs 23:18","Hebrews 6:19","1 Peter 1:3","Psalm 130:5",
   "Revelation 21:4","Psalm 34:18","Psalm 147:3","Psalm 30:5","Isaiah 43:2","Isaiah 54:10"],
 "trust": ["Psalm 56:3","Psalm 9:10","Isaiah 12:2","Psalm 37:5","Psalm 62:8","Nahum 1:7","Jeremiah 17:7-8","Psalm 20:7","Matthew 6:33-34","Psalm 91:1-2",
   "Psalm 23:1-4","Proverbs 29:25","Psalm 118:8","Psalm 55:22","Exodus 14:14","Deuteronomy 31:8","Psalm 16:8","Proverbs 18:10","Isaiah 26:4","2 Corinthians 5:7","Isaiah 55:8-9"],
 "purpose": ["Psalm 16:11","Philippians 4:4","Psalm 19:14","Psalm 139:14","Psalm 139:23-24","Psalm 51:10","Matthew 5:14-16","Matthew 7:7","Matthew 7:12",
   "Luke 6:38","Galatians 6:2","Hebrews 13:5","Hebrews 13:8","Philippians 4:8","Matthew 19:26","John 8:12","John 10:10","Acts 20:35","Romans 12:21",
   "Ephesians 3:20","Colossians 3:2","1 Thessalonians 5:11","1 John 1:7","Psalm 1:1-3","Psalm 32:8","Psalm 37:4","Psalm 145:18","Proverbs 11:25",
   "Isaiah 6:8","Jeremiah 33:3","Joshua 24:15","Psalm 133:1","John 15:11","Romans 12:15","Psalm 8:3-4"],
}

def clean(t):
    t = re.sub(r"\s+", " ", t).strip()
    return t

def fetch(ref):
    url = "https://bible-api.com/" + urllib.parse.quote(ref) + "?translation=web"
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "trynd-overlay-verse-builder"}), timeout=20) as r:
                return json.loads(r.read().decode("utf-8")), url
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10 + attempt * 5); continue
            raise
        except urllib.error.URLError:
            time.sleep(5); continue
    raise RuntimeError("failed " + ref)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "verses.js")
    verses, seen = [], set()
    for theme, refs in REFS.items():
        for ref in refs:
            if ref in seen: continue
            seen.add(ref)
            d, url = fetch(ref)
            if d.get("translation_id") != "web" or not d.get("text"):
                print("SKIP", ref, d.get("error")); continue
            verses.append({"ref": d["reference"], "text": clean(d["text"]), "translation": "WEB", "theme": theme})
            print(len(verses), d["reference"], "|", clean(d["text"])[:60], flush=True)
            time.sleep(2.1)
    stamp = time.strftime("%Y-%m-%d")
    with open(out, "w", encoding="utf-8") as f:
        f.write("// Verse of the day list. Text fetched from https://bible-api.com (translation=web) on %s.\n" % stamp)
        f.write("// World English Bible (WEB) - Public Domain. Rebuild with: python tools/build_verses.py\n")
        f.write("window.VERSES = " + json.dumps(verses, ensure_ascii=False, indent=1) + ";\n")
    print("wrote", out, len(verses))

if __name__ == "__main__":
    main()
