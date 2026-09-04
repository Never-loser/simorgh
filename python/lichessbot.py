"""Play Simorgh on Lichess as a BOT account, to get a real rating.

Every other measurement in this project is relative: Simorgh against
itself, or against one opponent whose own calibration is approximate. A
Lichess rating is different -- it comes from Glicko-2 over games against
thousands of rated opponents, and it is directly comparable with every
other bot and player on the site.

Setup (you do these once, not this script):

  1. Create a NEW Lichess account that has never played a rated game.
     An account that has cannot become a bot.
  2. Create a token at https://lichess.org/account/oauth/token/create
     with the "bot:play" scope.
  3. Put it where this script can find it, WITHOUT pasting it into a
     shell command (shell history keeps those):

         setx LICHESS_TOKEN "your-token"        (Windows, new shell after)
         export LICHESS_TOKEN=your-token        (bash)

     or write it as the only line of data/lichess_token.txt, which is
     gitignored.
  4. Upgrade the account to BOT -- THIS IS PERMANENT AND CANNOT BE UNDONE:

         python python/lichessbot.py --upgrade

Then run it:

    python python/lichessbot.py

It accepts standard-chess challenges within the configured time controls,
declines the rest, and plays them with the engine. Leave it running; the
rating settles after a hundred games or so.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import random
import threading
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("this needs the requests package: python -m pip install requests")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from selfplay import find_engine  # noqa: E402

API = "https://lichess.org"
TOKEN_FILE = ROOT / "data" / "lichess_token.txt"


# ==========================================================================
# Token
# ==========================================================================
def load_token() -> str:
    token = os.environ.get("LICHESS_TOKEN", "").strip()
    if token:
        return token
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            return token
    sys.exit(
        "No token found.\n"
        "  Set the LICHESS_TOKEN environment variable, or put the token on\n"
        f"  the first line of {TOKEN_FILE}\n"
        "  Create one at https://lichess.org/account/oauth/token/create\n"
        "  with the 'bot:play' scope.")


def session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ==========================================================================
# Engine wrapper: one process per game
# ==========================================================================
class EngineProcess:
    def __init__(self, path: str, book: bool):
        self.p = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1, cwd=str(ROOT))
        self.send("uci")
        self.read_until("uciok")
        self.send(f"setoption name OwnBook value {'true' if book else 'false'}")
        self.send("ucinewgame")
        self.send("isready")
        self.read_until("readyok")

    def send(self, cmd: str) -> None:
        self.p.stdin.write(cmd + "\n")
        self.p.stdin.flush()

    def read_until(self, prefix: str) -> str:
        while True:
            line = self.p.stdout.readline()
            if not line:
                return ""
            line = line.rstrip()
            if line.startswith(prefix):
                return line

    def bestmove(self, moves: list[str], wtime: int, btime: int,
                 winc: int, binc: int) -> str:
        cmd = "position startpos"
        if moves:
            cmd += " moves " + " ".join(moves)
        self.send(cmd)
        # Hand the real clock to the engine so its own time management
        # decides; it already understands wtime/btime/winc/binc.
        self.send(f"go wtime {max(wtime, 1)} btime {max(btime, 1)} "
                  f"winc {winc} binc {binc}")
        parts = self.read_until("bestmove").split()
        return parts[1] if len(parts) > 1 else ""

    def quit(self) -> None:
        try:
            self.send("quit")
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


# ==========================================================================
# One game
# ==========================================================================
def play_game(s: requests.Session, game_id: str, me: str, engine_path: str,
              book: bool) -> None:
    engine = EngineProcess(engine_path, book)
    my_colour = None
    print(f"[{game_id}] started", flush=True)

    try:
        stream = s.get(f"{API}/api/bot/game/stream/{game_id}", stream=True,
                       timeout=(10, 300))
        for raw in stream.iter_lines():
            if not raw:
                continue  # keep-alive
            event = json.loads(raw)
            kind = event.get("type")

            if kind == "gameFull":
                white = (event.get("white") or {}).get("id", "")
                my_colour = "white" if white == me else "black"
                opponent = (event.get("black" if my_colour == "white"
                                      else "white") or {})
                print(f"[{game_id}] we are {my_colour} vs "
                      f"{opponent.get('name', '?')} "
                      f"({opponent.get('rating', '?')})", flush=True)
                state = event.get("state") or {}
            elif kind == "gameState":
                state = event
            else:
                continue  # chatLine, opponentGone, ...

            if state.get("status", "started") != "started":
                print(f"[{game_id}] finished: {state.get('status')} "
                      f"winner={state.get('winner', '-')}", flush=True)
                return

            moves = (state.get("moves") or "").split()
            our_turn = (len(moves) % 2 == 0) == (my_colour == "white")
            if not our_turn:
                continue

            move = engine.bestmove(moves,
                                   state.get("wtime", 60000),
                                   state.get("btime", 60000),
                                   state.get("winc", 0),
                                   state.get("binc", 0))
            if not move or move == "0000":
                print(f"[{game_id}] engine had no move", flush=True)
                return

            reply = s.post(f"{API}/api/bot/game/{game_id}/move/{move}",
                           timeout=15)
            if reply.status_code != 200:
                # Usually means the game ended under us, or the move was
                # rejected. Either way, stop rather than spam the API.
                print(f"[{game_id}] move {move} rejected "
                      f"({reply.status_code} {reply.text[:120]})", flush=True)
                return
    except Exception as exc:
        print(f"[{game_id}] error: {exc}", flush=True)
    finally:
        engine.quit()


# ==========================================================================
# Outgoing challenges
# ==========================================================================
def online_bots(s: requests.Session, limit: int = 200) -> list[str]:
    """Usernames of bots currently online."""
    try:
        r = s.get(f"{API}/api/bot/online", params={"nb": limit},
                  stream=True, timeout=(10, 30))
        names = []
        for raw in r.iter_lines():
            if not raw:
                continue
            try:
                names.append(json.loads(raw)["username"])
            except Exception:
                continue
        return names
    except Exception:
        return []


def challenge_loop(s: requests.Session, args, active: dict, me: str,
                   stop: threading.Event) -> None:
    """Keep games flowing by challenging other online bots.

    Deliberately unhurried: Lichess rate-limits challenges, and a bot that
    hammers the endpoint gets throttled or banned. One challenge at a time,
    a pause between them, and a hard back-off on 429.
    """
    recent: list[str] = []
    backoff = args.challenge_every

    while not stop.wait(backoff):
        if len(active) >= args.max_games:
            continue

        bots = [b for b in online_bots(s) if b.lower() != me.lower()]
        # Avoid pestering the same few bots over and over.
        fresh = [b for b in bots if b not in recent] or bots
        if not fresh:
            continue

        target = random.choice(fresh)
        recent.append(target)
        del recent[:-40]

        try:
            r = s.post(f"{API}/api/challenge/{target}", timeout=20, data={
                "rated": "true" if args.rated else "false",
                "clock.limit": args.challenge_clock,
                "clock.increment": args.challenge_increment,
                "color": "random",
                "variant": "standard",
            })
        except Exception as exc:
            print(f"challenge failed: {exc}", flush=True)
            continue

        if r.status_code == 429:
            backoff = min(backoff * 2, 300)
            print(f"rate limited; backing off to {backoff}s", flush=True)
            continue

        backoff = args.challenge_every
        if r.status_code in (200, 201):
            print(f"challenged {target}", flush=True)
        # 4xx here is routine: the bot may be busy, or decline our time
        # control. Nothing to do but try someone else.


# ==========================================================================
# Incoming challenges
# ==========================================================================
def acceptable(c: dict, args) -> tuple[bool, str]:
    if c.get("variant", {}).get("key") != "standard":
        return False, "standard"
    speed = c.get("speed", "")
    if speed in ("correspondence", "classical"):
        return False, "tooSlow"
    if c.get("rated") and not args.rated:
        return False, "casual"
    if not c.get("rated") and args.rated_only:
        return False, "rated"

    clock = c.get("timeControl") or {}
    limit = clock.get("limit")
    if limit is None:
        return False, "timeControl"
    if limit < args.min_clock or limit > args.max_clock:
        return False, "timeControl"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upgrade", action="store_true",
                    help="one-time, PERMANENT upgrade of the account to BOT")
    ap.add_argument("--book", action="store_true",
                    help="let the engine use its opening book (recommended "
                         "for real play; off by default so ratings measure "
                         "the engine itself)")
    ap.add_argument("--rated", action="store_true", default=True,
                    help="accept rated challenges (default: yes -- casual "
                         "games do not produce a rating)")
    ap.add_argument("--rated-only", action="store_true",
                    help="decline casual challenges")
    ap.add_argument("--min-clock", type=int, default=60,
                    help="shortest initial clock in seconds")
    ap.add_argument("--max-clock", type=int, default=900,
                    help="longest initial clock in seconds")
    ap.add_argument("--max-games", type=int, default=2,
                    help="concurrent games")
    ap.add_argument("--challenge", action="store_true",
                    help="also challenge other online bots. Without this the "
                         "bot only waits to be challenged, which for a new "
                         "account means it never plays at all.")
    ap.add_argument("--challenge-clock", type=int, default=180,
                    help="initial clock in seconds for challenges we send")
    ap.add_argument("--challenge-increment", type=int, default=2)
    ap.add_argument("--challenge-every", type=int, default=25,
                    help="seconds between challenge attempts")
    ap.add_argument("--engine", default=None)
    args = ap.parse_args()

    token = load_token()
    s = session(token)

    if args.upgrade:
        print("This PERMANENTLY converts the account into a BOT account.")
        print("It cannot be undone, and the account can never play as a")
        print("human again. It must not have played any rated game yet.")
        if input("Type UPGRADE to continue: ").strip() != "UPGRADE":
            print("aborted")
            return 1
        r = s.post(f"{API}/api/bot/account/upgrade", timeout=20)
        print(r.status_code, r.text[:300])
        return 0 if r.status_code == 200 else 1

    who = s.get(f"{API}/api/account", timeout=20)
    if who.status_code != 200:
        sys.exit(f"token rejected ({who.status_code}). Check the token and "
                 f"that it has the bot:play scope.")
    me = who.json()
    if who.json().get("title") != "BOT":
        sys.exit("this account is not a BOT account yet -- run with "
                 "--upgrade first (permanent).")
    my_id = me["id"]
    print(f"connected as {me.get('username')} "
          f"(book {'on' if args.book else 'off'})", flush=True)

    engine_path = args.engine or find_engine()
    active: dict[str, threading.Thread] = {}

    stop = threading.Event()
    if args.challenge:
        threading.Thread(target=challenge_loop,
                         args=(s, args, active, my_id, stop),
                         daemon=True).start()
        print(f"challenging online bots every ~{args.challenge_every}s at "
              f"{args.challenge_clock}+{args.challenge_increment}",
              flush=True)
    else:
        print("waiting to be challenged. A new bot is rarely challenged by "
              "anyone -- pass --challenge to seek games.", flush=True)

    while True:
        try:
            stream = s.get(f"{API}/api/stream/event", stream=True,
                           timeout=(10, 300))
            for raw in stream.iter_lines():
                for gid in [g for g, t in active.items() if not t.is_alive()]:
                    active.pop(gid, None)
                if not raw:
                    continue
                event = json.loads(raw)
                kind = event.get("type")

                if kind == "challenge":
                    c = event["challenge"]
                    cid = c["id"]
                    if c.get("challenger", {}).get("id") == my_id:
                        continue  # our own outgoing challenge
                    ok, reason = acceptable(c, args)
                    if len(active) >= args.max_games:
                        ok, reason = False, "later"
                    if ok:
                        s.post(f"{API}/api/challenge/{cid}/accept", timeout=15)
                        print(f"accepted {cid} from "
                              f"{c.get('challenger', {}).get('name')}",
                              flush=True)
                    else:
                        s.post(f"{API}/api/challenge/{cid}/decline",
                               data={"reason": reason}, timeout=15)

                elif kind == "gameStart":
                    gid = event["game"]["id"]
                    if gid in active:
                        continue
                    t = threading.Thread(
                        target=play_game,
                        args=(s, gid, my_id, engine_path, args.book),
                        daemon=True)
                    active[gid] = t
                    t.start()

        except KeyboardInterrupt:
            print("\nstopping")
            stop.set()
            return 0
        except Exception as exc:
            print(f"event stream dropped ({exc}); reconnecting in 5s",
                  flush=True)
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
