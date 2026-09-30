"""Offline tests for scripts/update_rank.py with MOCKED Riot responses.
Run:  python -m unittest discover -s tests -v
No network, no key. All rank values below are FAKE test fixtures (not Caleb's rank) and are only
written to temporary folders - the real rank.json in the repo is never touched."""
import datetime as dt
import email.message
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import update_rank as ur  # noqa: E402

FAKE_KEY = "RGAPI-MOCK-not-a-real-key"
ACC_URL = "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Caleb%20Cameron/ccxx"
LEAGUE_URL = "https://oc1.api.riotgames.com/lol/league/v4/entries/by-puuid/MOCK-PUUID-123"
ACCOUNT = {"puuid": "MOCK-PUUID-123", "gameName": "Caleb Cameron", "tagLine": "ccxx"}


def entry(tier="GOLD", rank="II", lp=42, wins=10, losses=8, queue="RANKED_SOLO_5x5"):
    return {"queueType": queue, "tier": tier, "rank": rank, "leaguePoints": lp, "wins": wins, "losses": losses,
            "puuid": "MOCK-PUUID-123", "leagueId": "mock"}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load(path):
    return json.loads(read(path))


class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def http_error(url, code, headers=None):
    h = email.message.Message()
    for k, v in (headers or {}).items():
        h[k] = v
    return urllib.error.HTTPError(url, code, "mock", h, io.BytesIO(b"{}"))


class FakeRiot:
    """Stands in for urllib.request.urlopen. routes: url -> list of responses (dict/list = 200 JSON, int = HTTP error)."""
    def __init__(self, routes):
        self.routes = {k: list(v) for k, v in routes.items()}
        self.calls = []

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.calls.append((url, req.get_header("X-riot-token")))
        if url not in self.routes or not self.routes[url]:
            raise http_error(url, 404)
        r = self.routes[url].pop(0) if len(self.routes[url]) > 1 else self.routes[url][0]
        if isinstance(r, int):
            raise http_error(url, r, {"Retry-After": "0"} if r == 429 else None)
        return FakeResp(json.dumps(r).encode())


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.out = os.path.join(self.dir, "rank.json")
        self.state = os.path.join(self.dir, "rank_state.json")
        placeholder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rank.json")
        shutil.copy(placeholder, self.out)  # start from the real EXAMPLE placeholder (copy)
        self.ghout = os.path.join(self.dir, "gh_output.txt")
        self.env = mock.patch.dict(os.environ, {"RIOT_API_KEY": FAKE_KEY, "GITHUB_OUTPUT": self.ghout}, clear=False)
        self.env.start()
        self.sleep = mock.patch("time.sleep", lambda s: None)
        self.sleep.start()

    def tearDown(self):
        self.env.stop(); self.sleep.stop()
        shutil.rmtree(self.dir)

    def main(self, fake, *extra, now=None):
        with mock.patch("urllib.request.urlopen", fake):
            if now:
                real_run = ur.run
                with mock.patch.object(ur, "run", lambda a, k: real_run(a, k, now=now)):
                    return ur.main(["--out", self.out, "--state", self.state, *extra])
            return ur.main(["--out", self.out, "--state", self.state, *extra])

    def rank(self):
        return load(self.out)

    def outputs(self):
        return dict(l.strip().split("=", 1) for l in read(self.ghout).splitlines() if "=" in l)

    def test_urls_header_and_output(self):
        fake = FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(queue="RANKED_FLEX_SR", tier="IRON"), entry()]]})
        self.assertEqual(self.main(fake), 0)
        self.assertEqual([c[0] for c in fake.calls], [ACC_URL, LEAGUE_URL])
        self.assertTrue(all(c[1] == FAKE_KEY for c in fake.calls), "key must be sent as X-Riot-Token header")
        r = self.rank()
        self.assertFalse(r["example"])
        self.assertEqual((r["tier"], r["division"], r["lp"]), ("GOLD", "II", 42))  # solo queue picked, not flex
        self.assertEqual((r["wins_today"], r["losses_today"], r["lp_today"]), (0, 0, 0))
        self.assertNotIn("_note", r)
        self.assertEqual(self.outputs()["rank_changed"], "true")
        self.assertNotIn(FAKE_KEY, read(self.out) + read(self.state))

    def test_today_counts_and_no_change_no_write(self):
        t0 = dt.datetime(2026, 9, 30, 9, 0, tzinfo=dt.timezone.utc)  # 19:00 Sydney
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(lp=42, wins=10, losses=8)]]}), now=t0)
        t1 = t0 + dt.timedelta(hours=2)
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(tier="GOLD", rank="I", lp=10, wins=13, losses=9)]]}), now=t1)
        r = self.rank()
        self.assertEqual((r["wins_today"], r["losses_today"], r["lp_today"]), (3, 1, 68))  # II 42 -> I 10 = +68
        mtime = os.path.getmtime(self.out)
        os.utime(self.out, (mtime - 100, mtime - 100))
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(tier="GOLD", rank="I", lp=10, wins=13, losses=9)]]}),
                  now=t1 + dt.timedelta(minutes=15))
        self.assertEqual(os.path.getmtime(self.out), mtime - 100, "unchanged rank must not rewrite rank.json")
        self.assertEqual(self.outputs()["changed"], "false")

    def test_sydney_midnight_resets_today(self):
        before = dt.datetime(2026, 9, 30, 13, 30, tzinfo=dt.timezone.utc)  # 23:30 Sydney 30 Sep
        after = dt.datetime(2026, 9, 30, 14, 30, tzinfo=dt.timezone.utc)   # 00:30 Sydney 1 Oct
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(wins=10, losses=8)]]}), now=before)
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(wins=11, losses=8, lp=60)]]}), now=before + dt.timedelta(minutes=20))
        self.assertEqual(self.rank()["wins_today"], 1)
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(wins=11, losses=8, lp=60)]]}), now=after)
        self.assertEqual(load(self.state)["date"], "2026-10-01")
        self.assertEqual(self.rank()["wins_today"], 0)

    def test_apex_has_no_division(self):
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(tier="MASTER", rank="I", lp=120)]]}))
        self.assertEqual((self.rank()["tier"], self.rank()["division"]), ("MASTER", ""))

    def test_unranked(self):
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[]]}))
        r = self.rank()
        self.assertEqual((r["tier"], r["show_today"], r["example"]), ("UNRANKED", False, False))

    def test_expired_key_leaves_placeholder(self):
        before = read(self.out)
        self.assertEqual(self.main(FakeRiot({ACC_URL: [403]})), 0)
        self.assertEqual(read(self.out), before)
        self.assertEqual(self.outputs()["changed"], "false")
        self.assertEqual(self.main(FakeRiot({ACC_URL: [401]}), "--strict"), 1)
        self.assertTrue(load(self.out)["example"])

    def test_rate_limit_retry(self):
        fake = FakeRiot({ACC_URL: [429, ACCOUNT], LEAGUE_URL: [[entry()]]})
        self.assertEqual(self.main(fake), 0)
        self.assertEqual(len([c for c in fake.calls if c[0] == ACC_URL]), 2)
        self.assertEqual(self.rank()["tier"], "GOLD")

    def test_bad_response_is_rejected(self):
        before = read(self.out)
        self.main(FakeRiot({ACC_URL: [ACCOUNT], LEAGUE_URL: [[entry(tier="WOOD")]]}))
        self.assertEqual(read(self.out), before)
        self.main(FakeRiot({ACC_URL: [{"nope": 1}]}))
        self.assertEqual(read(self.out), before)

    def test_no_key_is_a_noop(self):
        before = read(self.out)
        with mock.patch.dict(os.environ, {"RIOT_API_KEY": ""}):
            fake = FakeRiot({})
            self.assertEqual(self.main(fake), 0)
            self.assertEqual(fake.calls, [])
        self.assertEqual(read(self.out), before)
        self.assertTrue(self.rank()["example"])


class RepoSafetyTests(unittest.TestCase):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_repo_placeholder_is_marked_example(self):
        r = load(os.path.join(self.ROOT, "rank.json"))
        self.assertTrue(r["example"])

    def test_no_riot_key_in_client_files(self):
        import re
        pat = re.compile(r"RGAPI-[0-9a-f]{8}-", re.I)
        for dp, dn, fn in os.walk(self.ROOT):
            dn[:] = [d for d in dn if d not in (".git", "tests", "__pycache__")]
            for f in fn:
                if f.endswith((".html", ".js", ".json", ".md", ".yml", ".toml", ".py")):
                    txt = read(os.path.join(dp, f))
                    self.assertIsNone(pat.search(txt), f"Riot key pattern found in {f}")
                    if f.endswith((".html", ".js")):
                        self.assertNotIn("riotgames.com", txt.replace("developer.riotgames.com", ""),
                                         f"client file {f} must not call the Riot API")


if __name__ == "__main__":
    unittest.main()
