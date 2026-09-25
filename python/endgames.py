"""Builds data/endgames.json, the endgame lessons both apps teach from.

Each lesson is a position, a goal and the method, in Persian and English.
The player practises it against the engine at full strength. Every
position is checked before it is written: python-chess must find it
legal, and the Syzygy endgame tablebase (through Lichess's public server)
must say the goal can be reached -- a win where the goal is to win, a draw
where it is to hold. The tablebase is exact for up to seven pieces, which
covers every lesson here; Simorgh's own score is printed beside it for
comparison, but an engine can miss a win beyond its horizon and so is not
what decides.

    python python/endgames.py
"""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "endgames.json"

GROUPS = [
    {"id": "mates", "fa": "مات‌های پایه", "en": "Basic mates"},
    {"id": "pawns", "fa": "آخربازی پیاده", "en": "Pawn endings"},
    {"id": "rooks", "fa": "آخربازی رخ", "en": "Rook endings"},
]

# goal: "mate" -- checkmate the engine; "promote" -- make a queen;
# "hold" -- stop the engine promoting for `limit` moves. `limit` is in the
# player's moves.
ENDGAMES = [
    {
        "id": "queen-mate", "group": "mates", "goal": "mate", "limit": 20,
        "fen": "8/8/8/4k3/8/8/8/4K2Q w - - 0 1",
        "name": {"fa": "مات با وزیر", "en": "Mate with the queen"},
        "summary": {
            "fa": "شاه و وزیر در برابر شاه تنها همیشه برنده است. کار وزیر این است که شاه حریف را به لبه‌ی صفحه براند؛ کار شاه این است که برای مات نزدیک بیاید.",
            "en": "King and queen against a lone king always wins. The queen drives the enemy king to the edge; your own king comes up to help mate it.",
        },
        "steps": {
            "fa": ["وزیر را یک «حرکت اسب» دورتر از شاه حریف بگذار: این شاه را در یک جعبه زندانی می‌کند.",
                   "با هر حرکت وزیر جعبه را کوچک‌تر کن تا شاه حریف به لبه برسد.",
                   "مراقب پات باش: همیشه دست‌کم یک خانه برای شاه حریف بگذار تا لحظه‌ی مات.",
                   "وقتی شاه حریف روی لبه است، شاه خودت را نزدیک بیاور و با وزیر مات کن."],
            "en": ["Put the queen a knight's move away from the enemy king: that shuts it in a box.",
                   "Shrink the box with each queen move until the king reaches the edge.",
                   "Beware of stalemate: always leave the king at least one square until the mate.",
                   "Once the king is on the edge, bring your own king up and mate with the queen."],
        },
    },
    {
        "id": "rook-mate", "group": "mates", "goal": "mate", "limit": 30,
        "fen": "8/8/8/4k3/8/8/8/R3K3 w - - 0 1",
        "name": {"fa": "مات با رخ", "en": "Mate with the rook"},
        "summary": {
            "fa": "شاه و رخ هم همیشه برنده است، ولی رخ به‌تنهایی نمی‌تواند شاه را براند و شاه خودی باید کمک کند. این مات حدود ۱۶ حرکت طول می‌کشد.",
            "en": "King and rook always wins too, but the rook cannot drive the king alone; your king has to help. It takes about 16 moves.",
        },
        "steps": {
            "fa": ["رخ یک ستون یا ردیف را می‌بندد و شاه حریف را در یک جعبه نگه می‌دارد.",
                   "شاه خودت را به شاه حریف نزدیک کن تا روبه‌روی هم بایستند (اپوزیسیون).",
                   "وقتی شاه‌ها روبه‌رو هستند، با رخ کیش بده تا جعبه یک ردیف کوچک شود.",
                   "اگر شاه‌ها روبه‌رو نیستند، یک حرکت انتظار با رخ بزن تا شاه حریف مجبور شود روبه‌روی شاه تو بیاید."],
            "en": ["The rook cuts off a rank or file, keeping the enemy king in a box.",
                   "Bring your king up until the two kings face each other (the opposition).",
                   "With the kings facing, check with the rook: the box shrinks by a rank.",
                   "If the kings do not face, make a waiting move with the rook so the enemy king has to step in front of yours."],
        },
    },
    {
        "id": "ladder-mate", "group": "mates", "goal": "mate", "limit": 10,
        "fen": "8/8/3k4/8/8/8/8/RR2K3 w - - 0 1",
        "name": {"fa": "مات نردبانی با دو رخ", "en": "The two-rook ladder"},
        "summary": {
            "fa": "دو رخ بدون کمک شاه مات می‌کنند: یکی ردیف را می‌بندد و دیگری کیش می‌دهد، پله به پله، مثل بالا رفتن از نردبان.",
            "en": "Two rooks mate without the king's help: one guards a rank, the other checks on the next, step by step, like climbing a ladder.",
        },
        "steps": {
            "fa": ["یک رخ ردیفی را می‌بندد که شاه حریف نمی‌تواند از آن رد شود.",
                   "رخ دیگر روی ردیف بعدی کیش می‌دهد و شاه یک ردیف عقب می‌رود.",
                   "رخ‌ها به نوبت جابه‌جا می‌شوند تا شاه به لبه برسد و مات شود.",
                   "اگر شاه حریف به یکی از رخ‌ها نزدیک شد، آن رخ را به سمت دیگر صفحه ببر."],
            "en": ["One rook guards a rank the enemy king cannot cross.",
                   "The other checks on the next rank, and the king has to step back.",
                   "The rooks take turns until the king is on the edge and mated.",
                   "If the king comes near one of the rooks, move that rook to the far side of the board."],
        },
    },
    {
        "id": "square-rule", "group": "pawns", "goal": "promote", "limit": 6,
        "fen": "7K/8/8/8/P7/8/6k1/8 w - - 0 1",
        "name": {"fa": "قاعده‌ی مربع", "en": "The rule of the square"},
        "summary": {
            "fa": "آیا شاه حریف به پیاده‌ی تو می‌رسد؟ بدون شمردن خانه‌ها هم می‌شود فهمید: از پیاده تا خانه‌ی تبدیل یک مربع بکش.",
            "en": "Can the enemy king catch your pawn? You can tell without counting squares: draw a square from the pawn to its promotion square.",
        },
        "steps": {
            "fa": ["مربعی بکش که یک ضلعش از پیاده تا خانه‌ی تبدیل است (اینجا a4 تا a8، پس مربع a4 تا e8).",
                   "اگر شاه حریف با نوبت خودش بتواند وارد این مربع شود، به پیاده می‌رسد.",
                   "اینجا شاه g2 خیلی دور است: پیاده بدون کمک شاه خودی تبدیل می‌شود.",
                   "پس وقت را با شاه هدر نده و مستقیم پیاده را جلو ببر."],
            "en": ["Draw the square whose side runs from the pawn to its promotion square (here a4 to a8, so the square a4-e8).",
                   "If the enemy king can step into that square on its move, it catches the pawn.",
                   "Here the king on g2 is too far: the pawn queens without help.",
                   "So do not waste time with your king: push the pawn."],
        },
    },
    {
        "id": "opposition", "group": "pawns", "goal": "promote", "limit": 20,
        "fen": "8/8/4k3/8/4K3/8/4P3/8 w - - 0 1",
        "name": {"fa": "اپوزیسیون و حرکت انتظار", "en": "The opposition and a spare move"},
        "summary": {
            "fa": "در آخربازی شاه و پیاده، این‌که نوبت کیست همه‌چیز است. وقتی شاه‌ها با یک خانه فاصله روبه‌رو هستند، طرفی که نوبتش نیست «اپوزیسیون» را دارد و برنده‌ی جنگ شاه‌هاست.",
            "en": "In king-and-pawn endings, whose move it is decides everything. With the kings facing one square apart, the side not to move has the opposition and wins the battle of the kings.",
        },
        "steps": {
            "fa": ["شاه‌ها روی e4 و e6 روبه‌روی هم‌اند و نوبت سفید است: اپوزیسیون با سیاه است.",
                   "ولی سفید یک حرکت انتظار دارد: پیاده‌ی e2 یک خانه جلو می‌رود و نوبت به سیاه می‌رسد.",
                   "حالا شاه سیاه باید کنار برود و شاه سفید به ردیف پنجم جلوی پیاده می‌رسد.",
                   "شاهی که جلوی پیاده‌اش روی ردیف ششم برسد، پیاده را تبدیل می‌کند."],
            "en": ["The kings face each other on e4 and e6 and it is White's move: Black has the opposition.",
                   "But White has a spare move: the e2 pawn steps forward one square, and now Black must move.",
                   "Black's king has to give way, and White's king gets to the fifth rank in front of the pawn.",
                   "A king that reaches the sixth rank in front of its pawn queens it."],
        },
    },
    {
        "id": "rook-pawn-draw", "group": "pawns", "goal": "hold", "limit": 20,
        "fen": "8/k7/8/1K6/P7/8/8/8 b - - 0 1",
        "name": {"fa": "پیاده‌ی رخ: مساوی کردن", "en": "The rook's pawn: holding the draw"},
        "summary": {
            "fa": "این بار شما دفاع می‌کنید. پیاده‌ی ستون a یا h با شاه تنها برنده نمی‌شود، به شرط این‌که شاه مدافع به گوشه برسد: شاه مهاجم نمی‌تواند از آن‌جا بیرونش کند.",
            "en": "This time you defend. A rook's pawn with a lone king cannot win if the defending king reaches the corner: the attacking king cannot drive it out.",
        },
        "steps": {
            "fa": ["شاه را به گوشه‌ی a8 یا نزدیکش برسان و آن‌جا بمان.",
                   "بین a8 و b8 (یا خانه‌های کنار گوشه) رفت و برگشت کن.",
                   "اگر شاه سفید راه را ببندد، پات می‌شود و آن هم مساوی است.",
                   "هدف: ۲۰ حرکت دوام بیاور بدون این‌که پیاده تبدیل شود."],
            "en": ["Get your king to the a8 corner or next to it, and stay there.",
                   "Shuffle between a8 and b8 (or the squares by the corner).",
                   "If White's king blocks you in, it is stalemate, which is a draw too.",
                   "Goal: last 20 moves without the pawn queening."],
        },
    },
    {
        "id": "lucena", "group": "rooks", "goal": "promote", "limit": 15,
        "fen": "1K1k4/1P6/8/8/8/8/r7/2R5 w - - 0 1",
        "name": {"fa": "پوزیسیون لوسنا: ساختن پل", "en": "The Lucena position: building a bridge"},
        "summary": {
            "fa": "مهم‌ترین وضعیت در آخربازی رخ. شاه سفید جلوی پیاده گیر افتاده و رخ سیاه از کنار کیش می‌دهد. راه برد: «ساختن پل» با رخ روی ردیف چهارم.",
            "en": "The most important position in rook endings. White's king is stuck in front of its pawn and Black's rook checks from the side. The way to win: build a bridge with the rook on the fourth rank.",
        },
        "steps": {
            "fa": ["با کیش رخ، شاه سیاه را یک ستون دیگر از پیاده دور کن (Rd1+).",
                   "رخ را به ردیف چهارم ببر (Rd4): این پل است.",
                   "شاه از پشت پیاده بیرون می‌آید؛ رخ سیاه از پشت کیش می‌دهد.",
                   "وقتی شاه به ستون c یا a نزدیک ردیف چهار رسید، رخ را جلوی کیش‌ها بگذار: پل کامل شد و پیاده تبدیل می‌شود."],
            "en": ["Check to push Black's king one more file away from the pawn (Rd1+).",
                   "Take the rook to the fourth rank (Rd4): that is the bridge.",
                   "The king steps out from in front of the pawn; Black's rook checks from behind.",
                   "When the king comes down near the fourth rank, put the rook in the way of the checks: the bridge is built and the pawn queens."],
        },
    },
]


def find_engine() -> str:
    for c in (ROOT / "cpp" / "build" / "simorgh.exe", ROOT / "cpp" / "build" / "simorgh"):
        if c.exists():
            return str(c)
    sys.exit("build the engine first (cpp/build)")


def engine_score(fens: list[str]) -> list[str]:
    """Simorgh's full-strength score for each position, from the side to move."""
    cmds = "".join(f"position fen {f}\nanalyse depth 18\n" for f in fens) + "quit\n"
    out = subprocess.run([find_engine()], input=cmds, capture_output=True, text=True, cwd=ROOT).stdout
    return [l.split(" score ")[1].split(" best ")[0] for l in out.splitlines() if l.startswith("analysis ")]


def tablebase(fen: str) -> str:
    """"win", "draw" or "loss" for the side to move, from Syzygy."""
    url = "https://tablebase.lichess.ovh/standard?fen=" + fen.replace(" ", "_")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)["category"]
        except OSError:
            time.sleep(2 + attempt * 3)
    sys.exit("the tablebase server did not answer")


def main():
    groups = {g["id"] for g in GROUPS}
    for e in ENDGAMES:
        assert e["group"] in groups, e["id"]
        b = chess.Board(e["fen"])
        if not b.is_valid():
            sys.exit(f"{e['id']}: not a legal position ({b.status()!r})")
        e["side"] = "w" if b.turn == chess.WHITE else "b"

    scores = engine_score([e["fen"] for e in ENDGAMES])
    for e, sc in zip(ENDGAMES, scores):
        truth = tablebase(e["fen"])
        want = "draw" if e["goal"] == "hold" else "win"
        ok = truth == want
        print(f"{e['id']:16} {e['goal']:8} tablebase {truth:5} engine {sc:10} {'ok' if ok else 'WRONG'}")
        if not ok:
            sys.exit(f"{e['id']}: the tablebase says {truth}, the lesson needs {want}")

    OUT.write_text(json.dumps({"groups": GROUPS, "endgames": ENDGAMES}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {len(ENDGAMES)} endgames to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
