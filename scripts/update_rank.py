#!/usr/bin/env python3
"""
update_rank.py (web / GitHub Actions version) - writes ../rank.json from the official Riot API.

Runs ONCE per call (GitHub Actions runs it about every 15 minutes, see .github/workflows/update-rank.yml).
Python 3.9+ standard library only.

The Riot API key is read ONLY from the RIOT_API_KEY environment variable
(in GitHub: Settings -> Secrets and variables -> Actions -> RIOT_API_KEY). It is never written to any file,
never printed, and never reaches the website: the browser only ever sees the finished rank.json.

  Riot ID   : Caleb Cameron#ccxx (override with env RIOT_ID or --riot-id)
  account-v1: https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
              (account-v1 only exists on americas / asia / europe; any works for any account, asia is nearest)
  league-v4 : https://oc1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}   (OCE platform = oc1)
  (match-v5 for OCE lives on "sea", but it is not needed for rank.)

Behaviour:
  * No key            -> prints a notice, leaves rank.json untouched (the EXAMPLE placeholder stays), exit 0.
  * Riot error        -> prints a warning, leaves rank.json untouched, exit 0 (use --strict to exit 1).
  * Nothing changed   -> files are not rewritten, so the workflow makes no commit.
  * "Today" W/L/LP is counted from the first check after midnight SYDNEY time (Australia/Sydney),
    using rank_state.json (committed next to rank.json).
  * Writes changed=true/false, rank_changed=..., state_changed=... to $GITHUB_OUTPUT when run in Actions.

Options: --queue solo|flex, --platform oc1, --account-region asia, --riot-id "Name#TAG",
         --out PATH, --state PATH, --hide-today, --reset-today, --strict, --dry-run (prints URLs, no key needed)
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from zoneinfo import ZoneInfo
    SYDNEY = ZoneInfo("Australia/Sydney")
except Exception:  # pragma: no cover - tzdata missing (not the case on GitHub's ubuntu runners)
    SYDNEY = dt.timezone(dt.timedelta(hours=10))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RIOT_ID = "Caleb Cameron#ccxx"
QUEUES = {"solo": "RANKED_SOLO_5x5", "flex": "RANKED_FLEX_SR"}
TIER_ORDER = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
DIV_ORDER = {"IV": 0, "III": 1, "II": 2, "I": 3}
APEX = {"MASTER", "GRANDMASTER", "CHALLENGER"}
VOLATILE = ("updated",)  # keys ignored when deciding whether rank.json really changed


class RiotError(Exception):
    pass


def split_riot_id(riot_id):
    if "#" not in riot_id:
        raise SystemExit('Riot ID must look like "Game Name#TAG"')
    name, tag = riot_id.rsplit("#", 1)
    return name.strip(), tag.strip()


def account_url(region, game_name, tag):
    q = lambda s: urllib.parse.quote(s, safe="")  # "Caleb Cameron" -> "Caleb%20Cameron"
    return f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{q(game_name)}/{q(tag)}"


def league_url(platform, puuid):
    return f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{urllib.parse.quote(puuid, safe='')}"


def riot_get(url, key, tries=4, sleep=time.sleep):
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"X-Riot-Token": key, "User-Agent": "trynd-overlay-web/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = min(60, int(e.headers.get("Retry-After") or 10)) if e.headers else 10
                print(f"  rate limited, waiting {wait}s")
                sleep(wait)
                continue
            if e.code in (401, 403):
                raise RiotError(f"HTTP {e.code}: Riot API key missing, invalid or expired. Development keys expire "
                                "every 24h - use a Personal API key (developer.riotgames.com) and update the "
                                "RIOT_API_KEY repository secret.")
            if e.code == 404:
                raise RiotError(f"HTTP 404: not found - check the Riot ID / platform. URL: {url}")
            if 500 <= e.code < 600 and attempt < tries - 1:
                sleep(3 * (attempt + 1))
                continue
            raise RiotError(f"HTTP {e.code} for {url}")
        except urllib.error.URLError as e:
            if attempt < tries - 1:
                sleep(3 * (attempt + 1))
                continue
            raise RiotError(f"network error: {e.reason}")
    raise RiotError("gave up after retries")


def ladder_value(tier, division, lp):
    """Rough 'total LP' so LP gained/lost today survives promotions/demotions."""
    tier = (tier or "").upper()
    if tier not in TIER_ORDER:
        return None
    if tier in APEX:
        return TIER_ORDER.index("MASTER") * 400 + int(lp or 0)
    return TIER_ORDER.index(tier) * 400 + DIV_ORDER.get((division or "").upper(), 0) * 100 + int(lp or 0)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def strip_volatile(d):
    return {k: v for k, v in (d or {}).items() if k not in VOLATILE}


def build_rank(args, entries, state, now):
    """Pure function: Riot league entries + saved state -> (rank_data, new_state)."""
    if not isinstance(entries, list):
        raise RiotError("unexpected league-v4 response (expected a list)")
    q = QUEUES[args.queue]
    today = now.astimezone(SYDNEY).date().isoformat()
    e = next((x for x in entries if isinstance(x, dict) and x.get("queueType") == q), None)
    if e is None:
        data = {"example": False, "label": args.label, "tier": "UNRANKED", "division": "", "lp": 0,
                "wins_today": 0, "losses_today": 0, "show_today": False}
        new_state = state
    else:
        tier = str(e.get("tier", "")).upper()
        if tier not in TIER_ORDER:
            raise RiotError(f"unexpected tier in Riot response: {tier!r}")
        div = str(e.get("rank", "")).upper()
        lp, w, l = int(e.get("leaguePoints", 0)), int(e.get("wins", 0)), int(e.get("losses", 0))
        new_state = dict(state or {})
        if args.reset_today or new_state.get("date") != today or new_state.get("queue") != q:
            new_state = {"date": today, "queue": q, "wins": w, "losses": l, "ladder": ladder_value(tier, div, lp)}
        lv, base = ladder_value(tier, div, lp), new_state.get("ladder")
        data = {
            "example": False,
            "label": args.label,
            "tier": tier, "division": "" if tier in APEX else div, "lp": lp,
            "wins_today": max(0, w - int(new_state.get("wins", w))),
            "losses_today": max(0, l - int(new_state.get("losses", l))),
            "lp_today": (lv - base) if (lv is not None and base is not None) else None,
            "season_wins": w, "season_losses": l,
            "show_today": not args.hide_today,
        }
    data["queue"] = q
    data["updated"] = now.astimezone(SYDNEY).isoformat(timespec="seconds")
    return data, new_state


def gh_output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def run(args, key, now=None, getter=riot_get):
    """Returns (rank_changed, state_changed)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    acc = getter(account_url(args.account_region, args.game_name, args.tag), key)
    if not isinstance(acc, dict) or not acc.get("puuid"):
        raise RiotError("unexpected account-v1 response (no puuid)")
    print(f"  Riot ID {acc.get('gameName')}#{acc.get('tagLine')} found")
    entries = getter(league_url(args.platform, acc["puuid"]), key)
    state = load_json(args.state, {})
    data, new_state = build_rank(args, entries, state, now)
    old = load_json(args.out, {})
    rank_changed = strip_volatile(old) != strip_volatile(data)
    state_changed = new_state != state and bool(new_state)
    if rank_changed:
        write_json(args.out, data)
    if state_changed:
        write_json(args.state, new_state)
    shown = f"{data['tier']} {data['division']} {data['lp']} LP".replace("  ", " ")
    print(f"  {shown}, today {data['wins_today']}W-{data['losses_today']}L -> "
          f"{'rank.json updated' if rank_changed else 'no change'}")
    return rank_changed, state_changed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write rank.json from the Riot API (one shot)")
    ap.add_argument("--riot-id", default=os.environ.get("RIOT_ID") or DEFAULT_RIOT_ID)
    ap.add_argument("--platform", default=os.environ.get("RIOT_PLATFORM") or "oc1", help="league-v4 platform (OCE = oc1)")
    ap.add_argument("--account-region", default="asia", choices=["americas", "asia", "europe"])
    ap.add_argument("--queue", default=os.environ.get("RANK_QUEUE") or "solo", choices=list(QUEUES))
    ap.add_argument("--label", default="Tryndamere OTP")
    ap.add_argument("--out", default=os.path.join(ROOT, "rank.json"))
    ap.add_argument("--state", default=os.path.join(ROOT, "rank_state.json"))
    ap.add_argument("--hide-today", action="store_true", help="don't show the Today W/L line")
    ap.add_argument("--reset-today", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on Riot errors (default: warn and exit 0)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    args.game_name, args.tag = split_riot_id(args.riot_id)

    if args.dry_run:
        print("account-v1:", account_url(args.account_region, args.game_name, args.tag))
        print("league-v4 :", league_url(args.platform, "{puuid-from-account-v1}"))
        return 0

    key = os.environ.get("RIOT_API_KEY", "").strip()
    if not key:
        print("::notice::RIOT_API_KEY secret is not set - rank.json left unchanged (EXAMPLE placeholder stays).")
        gh_output(changed="false", rank_changed="false", state_changed="false")
        return 0

    print(f"Checking {args.riot_id} on {args.platform} ({QUEUES[args.queue]})")
    try:
        rank_changed, state_changed = run(args, key)
    except (RiotError, KeyError, ValueError, TypeError) as e:
        print(f"::warning::Rank not updated: {e}")
        gh_output(changed="false", rank_changed="false", state_changed="false")
        return 1 if args.strict else 0
    gh_output(changed=str(rank_changed or state_changed).lower(),
              rank_changed=str(rank_changed).lower(), state_changed=str(state_changed).lower())
    return 0


if __name__ == "__main__":
    sys.exit(main())
