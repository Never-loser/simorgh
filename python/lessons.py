"""Builds data/lessons.json, the opening lessons both apps teach from.

Each lesson is a main line with a sentence on every move, in Persian and
English, plus a short summary and the key ideas. The lines are written here
in SAN for readability; this script plays every move with python-chess (so
an illegal or mistyped move stops the build), converts it to UCI, and looks
the final position up in data/openings.tsv so each lesson carries the ECO
code and name the engine will show when the line is played.

    python python/lessons.py

The written notes are the only part of a lesson that is not checked by a
program; the numbers the apps show beside them (what each move changed in
the evaluation) come from the engine at run time.
"""

import json
import sys
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "lessons.json"
TABLE = ROOT / "data" / "openings.tsv"

GROUPS = [
    {"id": "e4", "fa": "گشایش‌های e4 برای سفید", "en": "1.e4 openings for White"},
    {"id": "vs-e4", "fa": "دفاع در برابر e4", "en": "Defences to 1.e4"},
    {"id": "systems", "fa": "سیستم‌های سفید", "en": "Systems for White"},
    {"id": "vs-d4", "fa": "دفاع در برابر d4", "en": "Defences to 1.d4"},
]


def M(san, fa, en):
    return {"san": san, "fa": fa, "en": en}


LESSONS = [
    # ------------------------------------------------------------------ e4
    {
        "id": "italian", "group": "e4", "side": "w",
        "name": {"fa": "بازی ایتالیایی", "en": "Italian Game"},
        "summary": {
            "fa": "یکی از قدیمی‌ترین گشایش‌ها و بهترین جا برای یاد گرفتن اصول: مرکز، گسترش سریع و امنیت شاه.",
            "en": "One of the oldest openings, and the best place to learn the basics: the centre, quick development and king safety.",
        },
        "ideas": {
            "fa": ["مهره‌های سبک را زود بیرون بیاور و زود قلعه برو.",
                   "فیل‌ها روی c4 و c5 به نقطه‌های ضعیف f7 و f2 نشانه می‌روند.",
                   "نقشه‌ی سفید c3 و بعد d4 است تا مرکز را با دو پیاده بگیرد."],
            "en": ["Develop the minor pieces early and castle early.",
                   "The bishops on c4 and c5 aim at the weak points f7 and f2.",
                   "White's plan is c3 and then d4, to hold the centre with two pawns."],
        },
        "moves": [
            M("e4", "پیاده‌ی شاه مرکز را می‌گیرد و راه فیل و وزیر را باز می‌کند.",
              "The king's pawn takes the centre and opens lines for the bishop and queen."),
            M("e5", "سیاه هم سهمش از مرکز را می‌خواهد.",
              "Black claims a share of the centre too."),
            M("Nf3", "اسب به بهترین خانه‌اش می‌رود و به پیاده‌ی e5 حمله می‌کند.",
              "The knight develops to its best square and attacks the e5 pawn."),
            M("Nc6", "سیاه با گسترش اسب از e5 دفاع می‌کند.",
              "Black defends e5 while developing a knight."),
            M("Bc4", "فیل خانه‌ی f7 را نشانه می‌گیرد؛ f7 فقط با شاه دفاع می‌شود و ضعیف‌ترین نقطه‌ی سیاه است.",
              "The bishop aims at f7, guarded only by the king: the weakest point in Black's camp."),
            M("Bc5", "سیاه آینه‌وار جواب می‌دهد و f2 را نشانه می‌گیرد. این «جوکو پیانو» یعنی «بازی آرام» است.",
              "Black mirrors it and aims at f2. This is the Giuoco Piano, the 'quiet game'."),
            M("c3", "سفید d4 را آماده می‌کند تا مرکز را با دو پیاده بگیرد.",
              "White prepares d4, to build a centre of two pawns."),
            M("Nf6", "سیاه با حمله به e4 گسترش می‌یابد و فشار را به سفید برمی‌گرداند.",
              "Black develops with an attack on e4, handing the question back to White."),
            M("d3", "سفید راه آرام را انتخاب می‌کند: e4 محکم می‌شود و مرکز فعلاً بسته می‌ماند.",
              "White takes the slow road: e4 is secured and the centre stays closed for now."),
            M("d6", "سیاه هم e5 را محکم می‌کند و راه فیل c8 را باز می‌کند.",
              "Black secures e5 as well and opens the c8 bishop's diagonal."),
            M("O-O", "شاه به جای امن می‌رود و رخ به مرکز نزدیک می‌شود.",
              "The king goes to safety and the rook comes towards the centre."),
            M("O-O", "سیاه هم قلعه می‌رود. گسترش هر دو طرف تمام است و وسط‌بازی شروع می‌شود.",
              "Black castles too. Both sides are developed and the middlegame begins."),
        ],
    },
    {
        "id": "ruy-lopez", "group": "e4", "side": "w",
        "name": {"fa": "روی لوپز (اسپانیایی)", "en": "Ruy Lopez (Spanish)"},
        "summary": {
            "fa": "سفید بی‌سروصدا ولی پیوسته به مرکز سیاه فشار می‌آورد. از قرن نوزدهم تا امروز گشایش محبوب قهرمانان جهان.",
            "en": "White presses on Black's centre quietly but constantly. A favourite of world champions from the 19th century to today.",
        },
        "ideas": {
            "fa": ["فشار غیرمستقیم روی e5، از راه حمله به اسبی که از آن دفاع می‌کند.",
                   "قلعه‌ی زود و رخ روی ستون e.",
                   "نقشه‌ی c3 و d4 برای یک مرکز بزرگ."],
            "en": ["Indirect pressure on e5, by attacking the knight that defends it.",
                   "Castle early and put a rook on the e-file.",
                   "The plan c3 and d4, for a big centre."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("e5", "سیاه هم همین کار را می‌کند.", "Black does the same."),
            M("Nf3", "گسترش با حمله به e5.", "Development with an attack on e5."),
            M("Nc6", "دفاع از e5.", "Defending e5."),
            M("Bb5", "فیل به اسبی فشار می‌آورد که از e5 دفاع می‌کند. این «روی لوپز» یا گشایش اسپانیایی است.",
              "The bishop presses on the knight that defends e5. This is the Ruy Lopez, or Spanish Game."),
            M("a6", "سیاه از فیل می‌پرسد: عقب می‌روی یا تعویض می‌کنی؟",
              "Black asks the bishop: retreat or exchange?"),
            M("Ba4", "سفید فیل را نگه می‌دارد و فشار روی c6 را حفظ می‌کند.",
              "White keeps the bishop and the pressure on c6."),
            M("Nf6", "سیاه گسترش می‌یابد و به e4 حمله می‌کند.",
              "Black develops and hits e4."),
            M("O-O", "سفید به‌جای دفاع از e4 قلعه می‌رود؛ اگر سیاه e4 را بگیرد، با Re1 پس گرفته می‌شود.",
              "White castles instead of defending e4: if Black takes it, Re1 wins it back."),
            M("Be7", "سیاه آماده‌ی قلعه‌رفتن می‌شود. این «روی لوپز بسته» است.",
              "Black prepares to castle: the Closed Ruy Lopez."),
            M("Re1", "حالا رخ از e4 دفاع می‌کند و سفید واقعاً تهدید می‌کند با Bxc6 و بعد Nxe5 پیاده ببرد.",
              "Now the rook guards e4, and White really threatens Bxc6 followed by Nxe5."),
            M("b5", "سیاه فیل مزاحم را از قطر a4 تا e8 دور می‌کند.",
              "Black drives the bishop off the a4-e8 diagonal."),
            M("Bb3", "فیل روی قطر تازه‌ای می‌نشیند و باز f7 را نشانه می‌گیرد.",
              "The bishop settles on a new diagonal, aimed at f7 again."),
            M("d6", "سیاه e5 را محکم می‌کند و راه فیل c8 را باز می‌کند.",
              "Black secures e5 and frees the c8 bishop."),
            M("c3", "خانه‌ی c2 برای عقب‌نشینی فیل، و آماده‌کردن d4.",
              "A retreat square on c2 for the bishop, and preparation for d4."),
            M("O-O", "هر دو طرف آماده‌اند؛ نبرد اصلی بر سر مرکز و پیشروی d4 است.",
              "Both sides are ready; the fight will be about the centre and d4."),
        ],
    },
    {
        "id": "scotch", "group": "e4", "side": "w",
        "name": {"fa": "بازی اسکاتلندی", "en": "Scotch Game"},
        "summary": {
            "fa": "سفید مرکز را زود باز می‌کند. بازی باز و روشن است و سرعت گسترش از هر چیزی مهم‌تر است.",
            "en": "White opens the centre early. The game is open and clear-cut, and the speed of development matters most.",
        },
        "ideas": {
            "fa": ["باز کردن مرکز با d4 در حرکت سوم.",
                   "اسب قوی روی d4 و پیاده‌ی e4 که فضای بیشتری می‌دهد.",
                   "شمردن حمله‌ها و دفاع‌ها روی یک خانه، مثل d4."],
            "en": ["Opening the centre with d4 on move three.",
                   "A strong knight on d4, and the e4 pawn giving extra space.",
                   "Counting attackers and defenders of one square, like d4."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("e5", "سیاه هم همین کار را می‌کند.", "Black does the same."),
            M("Nf3", "گسترش با حمله به e5.", "Development with an attack on e5."),
            M("Nc6", "دفاع از e5.", "Defending e5."),
            M("d4", "سفید بی‌درنگ مرکز را باز می‌کند و دوباره به e5 حمله می‌کند.",
              "White opens the centre at once and attacks e5 again."),
            M("exd4", "سیاه نمی‌تواند e5 را نگه دارد و تعویض می‌کند.",
              "Black cannot hold e5 and takes."),
            M("Nxd4", "سفید با اسب پس می‌گیرد. سفید پیاده‌ی e4 را دارد و سیاه در مرکز پیاده‌ای ندارد: کمی فضای بیشتر برای سفید.",
              "White recaptures with the knight. White keeps a pawn on e4 and Black has none in the centre: a little more space."),
            M("Bc5", "سیاه فوراً به اسب مرکزی حمله می‌کند.",
              "Black attacks the centralised knight at once."),
            M("Be3", "سفید از اسب دفاع می‌کند و یک مهره‌ی دیگر را هم بیرون می‌آورد.",
              "White defends the knight and develops another piece."),
            M("Qf6", "وزیر هم به d4 حمله می‌کند: حالا سه مهره‌ی سیاه به d4 حمله کرده‌اند و فقط دو مهره‌ی سفید از آن دفاع می‌کنند.",
              "The queen joins in: three black pieces now attack d4, and only two white ones defend it."),
            M("c3", "پیاده‌ی c3 سومین مدافع d4 است و تعادل برمی‌گردد.",
              "The c3 pawn is the third defender of d4, and the balance is restored."),
            M("Nge7", "اسب به e7 می‌رود نه f6، تا جلوی وزیر را نگیرد.",
              "The knight goes to e7, not f6, so as not to block the queen."),
            M("Bc4", "سفید گسترش را ادامه می‌دهد و آماده‌ی قلعه‌رفتن می‌شود.",
              "White keeps developing and gets ready to castle."),
        ],
    },
    # --------------------------------------------------------------- vs e4
    {
        "id": "sicilian-najdorf", "group": "vs-e4", "side": "b",
        "name": {"fa": "دفاع سیسیلی: نایدورف", "en": "Sicilian Defence: Najdorf"},
        "summary": {
            "fa": "مبارزه‌جوترین جواب به e4. سیاه از حرکت اول تعادل را به هم می‌زند تا برای برد بازی کند.",
            "en": "The most combative answer to 1.e4. Black unbalances the game from move one, to play for a win.",
        },
        "ideas": {
            "fa": ["پیاده‌ی کناری c با پیاده‌ی مرکزی d سفید عوض می‌شود.",
                   "ستون نیمه‌باز c مال رخ‌های سیاه است.",
                   "بازی سیاه در جناح وزیر با a6 و بعد b5."],
            "en": ["A flank pawn (c) is traded for White's centre pawn (d).",
                   "The half-open c-file belongs to Black's rooks.",
                   "Black plays on the queenside with ...a6 and then ...b5."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("c5", "سیاه به‌جای تقارن، با پیاده‌ی کناری برای خانه‌ی d4 می‌جنگد. بازی از همین حرکت نامتقارن است.",
              "Instead of symmetry, Black fights for d4 with a flank pawn. The game is unbalanced from here."),
            M("Nf3", "گسترش و آماده‌کردن d4.", "Development, preparing d4."),
            M("d6", "سیاه e5 را کنترل می‌کند و راه فیل c8 را باز می‌کند.",
              "Black controls e5 and opens the c8 bishop."),
            M("d4", "سفید مرکز را باز می‌کند.", "White opens the centre."),
            M("cxd4", "ایده‌ی اصلی سیسیلی: پیاده‌ی کناری c با پیاده‌ی مرکزی سفید عوض می‌شود. حالا سیاه دو پیاده‌ی مرکزی دارد و سفید یکی.",
              "The whole idea of the Sicilian: a flank pawn for a centre pawn. Black now has two central pawns to White's one."),
            M("Nxd4", "سفید با اسب پس می‌گیرد و در گسترش جلوتر است.",
              "White recaptures and leads in development."),
            M("Nf6", "گسترش با حمله به e4.", "Developing with an attack on e4."),
            M("Nc3", "سفید از e4 دفاع می‌کند.", "White defends e4."),
            M("a6", "حرکت نایدورف: خانه‌ی b5 را از مهره‌های سفید می‌گیرد و b5 را برای سیاه آماده می‌کند. گشایش محبوب فیشر و کاسپاروف.",
              "The Najdorf move: it takes b5 away from White's pieces and prepares ...b5. A favourite of Fischer and Kasparov."),
        ],
    },
    {
        "id": "french", "group": "vs-e4", "side": "b",
        "name": {"fa": "دفاع فرانسوی", "en": "French Defence"},
        "summary": {
            "fa": "دفاعی محکم که مرکز را به سفید می‌دهد تا بعد به آن ضربه بزند. ضعف معروفش فیل c8 است که پشت پیاده‌ی e6 گیر می‌کند.",
            "en": "A solid defence that lets White have the centre, to strike at it later. Its known weakness is the c8 bishop, shut in behind e6.",
        },
        "ideas": {
            "fa": ["ضربه به زنجیره‌ی پیاده‌ی سفید با c5 و f6.",
                   "حمله به پایه‌ی زنجیره، یعنی d4.",
                   "حواست به فیل خانه‌سفید محبوس باشد."],
            "en": ["Strike at White's pawn chain with ...c5 and ...f6.",
                   "Attack the base of the chain, d4.",
                   "Look after the shut-in light-squared bishop."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("e6", "سیاه d5 را آماده می‌کند تا مرکز سفید را به چالش بکشد.",
              "Black prepares ...d5 to challenge White's centre."),
            M("d4", "سفید با دو پیاده مرکز را کامل می‌گیرد.", "White takes the full centre with two pawns."),
            M("d5", "سیاه به e4 حمله می‌کند؛ d5 با e6 محکم است.",
              "Black attacks e4; d5 is backed by e6."),
            M("Nc3", "از e4 دفاع می‌کند و گسترش می‌یابد.", "Defends e4 and develops."),
            M("Nf6", "فشار بیشتر روی e4.", "More pressure on e4."),
            M("Bg5", "فیل اسب f6 را، که به e4 فشار می‌آورد، به وزیر میخ می‌کند.",
              "The bishop pins the f6 knight, which presses on e4, to the queen."),
            M("Be7", "سیاه میخ را باز می‌کند.", "Black breaks the pin."),
            M("e5", "سفید با گرفتن فضا اسب را از f6 می‌راند. زنجیره‌ی پیاده‌ی d4 و e5 شکل می‌گیرد.",
              "White gains space and drives the knight away. The d4-e5 pawn chain is formed."),
            M("Nfd7", "اسب عقب می‌رود و آماده است با c5 و f6 به زنجیره حمله شود.",
              "The knight retreats, ready to support ...c5 and ...f6 against the chain."),
            M("Bxe7", "سفید فیل‌ها را عوض می‌کند.", "White trades bishops."),
            M("Qxe7", "نقشه‌ها روشن است: سفید در جناح شاه بازی می‌کند (مثلاً با f4)، سیاه با c5 به پایه‌ی زنجیره، d4، ضربه می‌زند.",
              "The plans are set: White plays on the kingside (f4, for example), Black strikes the base of the chain, d4, with ...c5."),
        ],
    },
    {
        "id": "caro-kann", "group": "vs-e4", "side": "b",
        "name": {"fa": "دفاع کاروکان", "en": "Caro-Kann Defence"},
        "summary": {
            "fa": "یکی از محکم‌ترین جواب‌ها به e4: ساختار پیاده‌ی سالم و فیلی که آزاد می‌ماند. سیاه کمی فضا می‌دهد ولی ضعفی ندارد.",
            "en": "One of the most solid answers to 1.e4: a healthy pawn structure and a bishop that stays free. Black gives a little space but has no weaknesses.",
        },
        "ideas": {
            "fa": ["فیل c8 قبل از e6 بیرون می‌آید.",
                   "ساختار محکم پیاده‌ها روی c6 و e6.",
                   "سیاه معمولاً آخر بازی را خوب بازی می‌کند، چون ضعف پیاده ندارد."],
            "en": ["The c8 bishop comes out before ...e6.",
                   "A solid pawn structure on c6 and e6.",
                   "Black is usually fine in the endgame: no pawn weaknesses."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("c6", "مثل فرانسوی d5 را آماده می‌کند، ولی راه فیل c8 را نمی‌بندد.",
              "Like the French it prepares ...d5, but without blocking the c8 bishop."),
            M("d4", "سفید مرکز را کامل می‌گیرد.", "White takes the full centre."),
            M("d5", "حمله به e4.", "Attacking e4."),
            M("Nc3", "از e4 دفاع می‌کند.", "Defends e4."),
            M("dxe4", "سیاه تعویض می‌کند تا مرکز سفید را کوچک کند.",
              "Black trades to reduce White's centre."),
            M("Nxe4", "اسب سفید در مرکز است.", "White's knight stands in the centre."),
            M("Bf5", "همان فیلی که در فرانسوی گیر می‌کند، اینجا قبل از e6 بیرون می‌آید و به اسب حمله می‌کند.",
              "The bishop that gets stuck in the French comes out before ...e6, attacking the knight."),
            M("Ng3", "اسب با حمله به فیل عقب می‌رود.", "The knight retreats with an attack on the bishop."),
            M("Bg6", "فیل روی قطر خوبش می‌ماند.", "The bishop stays on its good diagonal."),
            M("h4", "سفید تهدید می‌کند با h5 فیل را به دام بیندازد.",
              "White threatens h5, trapping the bishop."),
            M("h6", "سیاه خانه‌ی h7 را برای فیل آماده می‌کند.",
              "Black makes room on h7 for the bishop."),
            M("Nf3", "گسترش؛ اسب خانه‌ی e5 را هم نشانه می‌گیرد.", "Development; the knight also eyes e5."),
            M("Nd7", "اسب e5 را کنترل می‌کند و راه Ngf6 را باز می‌کند. ساختار سیاه بسیار محکم است.",
              "The knight controls e5 and prepares ...Ngf6. Black's structure is rock solid."),
        ],
    },
    {
        "id": "scandinavian", "group": "vs-e4", "side": "b",
        "name": {"fa": "دفاع اسکاندیناوی", "en": "Scandinavian Defence"},
        "summary": {
            "fa": "ساده و سرراست: سیاه مرکز را از حرکت اول باز می‌کند و در عوض کمی وقت، ساختاری محکم می‌گیرد.",
            "en": "Simple and direct: Black opens the centre on move one and, for a little time, gets a solid structure.",
        },
        "ideas": {
            "fa": ["باز کردن فوری مرکز.",
                   "وزیری که زود بیرون آمده باید جای امنی مثل a5 پیدا کند.",
                   "ساختار c6 و فیل فعال روی f5، شبیه کاروکان."],
            "en": ["Opening the centre at once.",
                   "An early queen needs a safe square, like a5.",
                   "The c6 structure and an active bishop on f5, as in the Caro-Kann."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("d5", "سیاه بی‌درنگ به e4 حمله می‌کند.", "Black attacks e4 at once."),
            M("exd5", "سفید می‌گیرد.", "White takes."),
            M("Qxd5", "وزیر پس می‌گیرد. بیرون آمدن زود وزیر معمولاً خطر دارد، چون حریف با حمله به آن وقت می‌خرد.",
              "The queen recaptures. An early queen is usually risky: the opponent gains time by attacking it."),
            M("Nc3", "درست همین: سفید با حمله به وزیر گسترش می‌یابد.",
              "Exactly that: White develops with an attack on the queen."),
            M("Qa5", "وزیر به a5 می‌رود، جایی که امن است و قطر e1 تا a5 را زیر نظر دارد.",
              "The queen goes to a5, where it is safe and watches the e1-a5 diagonal."),
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("Nf6", "گسترش.", "Development."),
            M("Nf3", "گسترش.", "Development."),
            M("c6", "خانه‌ی c7 برای عقب‌نشینی وزیر، و کنترل b5 و d5.",
              "A retreat square for the queen on c7, and control of b5 and d5."),
            M("Bc4", "گسترش؛ فیل f7 را نشانه می‌گیرد.", "Development; the bishop aims at f7."),
            M("Bf5", "فیل خانه‌سفید سیاه آزادانه بیرون می‌آید؛ ساختار شبیه کاروکان است.",
              "Black's light-squared bishop develops freely; the structure resembles the Caro-Kann."),
        ],
    },
    # ------------------------------------------------------------- systems
    {
        "id": "london", "group": "systems", "side": "w",
        "name": {"fa": "سیستم لندن", "en": "London System"},
        "summary": {
            "fa": "یک سیستم به‌جای یک خط: در برابر تقریباً هر دفاعی همین آرایش را می‌چینی. کم‌خطر و آسان برای یاد گرفتن.",
            "en": "A system rather than a line: you set up the same way against almost anything. Low-risk and easy to learn.",
        },
        "ideas": {
            "fa": ["فیل خانه‌سیاه قبل از e3 به f4 می‌رود.",
                   "هرم پیاده‌ی c3، d4 و e3 مرکز را محکم نگه می‌دارد.",
                   "نقشه‌ی حمله: اسب به e5 و مهره‌ها رو به جناح شاه."],
            "en": ["The dark-squared bishop goes to f4 before e3.",
                   "The c3-d4-e3 pawn pyramid holds the centre firmly.",
                   "The attacking plan: a knight on e5 and pieces aimed at the kingside."],
        },
        "moves": [
            M("d4", "پیاده‌ی وزیر مرکز را می‌گیرد؛ برخلاف e4 از قبل با وزیر دفاع شده است.",
              "The queen's pawn takes the centre; unlike e4 it is already guarded by the queen."),
            M("d5", "سیاه هم مرکز را می‌گیرد.", "Black takes the centre too."),
            M("Nf3", "گسترش.", "Development."),
            M("Nf6", "گسترش.", "Development."),
            M("Bf4", "حرکت شاخص لندن: فیل خانه‌سیاه قبل از e3 بیرون می‌آید تا پشت پیاده‌ها گیر نکند.",
              "The signature move: the dark-squared bishop comes out before e3, so it is not shut in."),
            M("e6", "سیاه راه فیل f8 را باز می‌کند.", "Black opens the f8 bishop."),
            M("e3", "ساختار محکم d4 و e3، و راه فیل f1 باز می‌شود.",
              "A solid d4-e3 structure, and the f1 bishop is free."),
            M("c5", "سیاه به d4 ضربه می‌زند.", "Black strikes at d4."),
            M("c3", "d4 محکم می‌شود و هرم c3، d4 و e3 شکل می‌گیرد.",
              "d4 is reinforced: the c3-d4-e3 pyramid."),
            M("Nc6", "فشار بیشتر روی d4.", "More pressure on d4."),
            M("Nbd2", "اسب ساختار را پشتیبانی می‌کند و بعداً می‌تواند به e5 یا f3 برود.",
              "The knight supports the structure and can later go to e5 or f3."),
            M("Bd6", "سیاه پیشنهاد می‌دهد فیل خوب سفید تعویض شود.",
              "Black offers to trade off White's good bishop."),
            M("Bg3", "سفید فیل را نگه می‌دارد؛ اگر سیاه روی g3 تعویض کند، hxg3 ستون h را برای رخ سفید باز می‌کند.",
              "White keeps the bishop; if Black takes on g3, hxg3 opens the h-file for White's rook."),
            M("O-O", "سیاه قلعه می‌رود.", "Black castles."),
            M("Bd3", "همه‌ی مهره‌ها به جناح شاه نگاه می‌کنند؛ نقشه‌ی سفید Ne5 و حمله است.",
              "Every piece now looks at the kingside: White's plan is Ne5 and an attack."),
        ],
    },
    {
        "id": "english", "group": "systems", "side": "w",
        "name": {"fa": "گشایش انگلیسی", "en": "English Opening"},
        "summary": {
            "fa": "گشایشی انعطاف‌پذیر و موضعی: بازی کندتر است و فهمیدن نقشه‌ها از حفظ کردن خط‌ها مهم‌تر است.",
            "en": "A flexible, positional opening: the game is slower, and understanding the plans matters more than memorising lines.",
        },
        "ideas": {
            "fa": ["کنترل مرکز از کنار، به‌خصوص خانه‌ی d5.",
                   "فیل فیانکتو روی g2 روی قطر بلند.",
                   "نقشه‌ی معمول سفید: Rb1 و b4 در جناح وزیر."],
            "en": ["Controlling the centre from the side, especially d5.",
                   "A fianchettoed bishop on g2, on the long diagonal.",
                   "White's usual plan: Rb1 and b4 on the queenside."],
        },
        "moves": [
            M("c4", "سفید مرکز را از کنار کنترل می‌کند، به‌خصوص d5.",
              "White controls the centre from the side, especially d5."),
            M("e5", "سیاه مرکز را با پیاده می‌گیرد: یک سیسیلی با رنگ‌های برعکس.",
              "Black takes the centre with a pawn: a Sicilian with colours reversed."),
            M("Nc3", "کنترل d5.", "Controlling d5."),
            M("Nc6", "گسترش.", "Development."),
            M("g3", "آماده‌کردن فیانکتو.", "Preparing a fianchetto."),
            M("g6", "سیاه هم همین را انتخاب می‌کند.", "Black chooses the same."),
            M("Bg2", "فیل روی قطر بلند، d5 و b7 را نشانه می‌گیرد.",
              "The bishop on the long diagonal eyes d5 and b7."),
            M("Bg7", "سیاه هم فیلش را فیانکتو می‌کند.", "Black fianchettoes too."),
            M("d3", "سفید آرام بازی می‌کند و مرکز را بسته نگه می‌دارد.",
              "White plays quietly and keeps the centre closed."),
            M("d6", "ساختار بسته و متقارن. نقشه‌ی سفید معمولاً Rb1 و b4 است، و سیاه در جناح شاه بازی می‌کند.",
              "A closed, symmetrical structure. White usually goes Rb1 and b4; Black plays on the kingside."),
        ],
    },
    # --------------------------------------------------------------- vs d4
    {
        "id": "qgd", "group": "vs-d4", "side": "b",
        "name": {"fa": "گامبی وزیرِ ردشده", "en": "Queen's Gambit Declined"},
        "summary": {
            "fa": "کلاسیک‌ترین دفاع در برابر d4: سیاه مرکز را محکم نگه می‌دارد. امن ولی کمی منفعل؛ مشکل اصلی فیل c8 است.",
            "en": "The most classical defence to 1.d4: Black holds the centre firmly. Safe but a little passive; the main problem is the c8 bishop.",
        },
        "ideas": {
            "fa": ["نگه داشتن d5 با e6 و c6.",
                   "آزاد کردن بازی در لحظه‌ی مناسب با c5 یا e5.",
                   "سفید روی ستون c فشار می‌آورد."],
            "en": ["Holding d5 with ...e6 and ...c6.",
                   "Freeing the game at the right moment with ...c5 or ...e5.",
                   "White presses on the c-file."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("d5", "سیاه مرکز را پس نمی‌دهد.", "Black holds his share of the centre."),
            M("c4", "گامبی وزیر: سفید پیاده‌ی c را پیشنهاد می‌دهد تا d5 را از مرکز دور کند. گامبی واقعی نیست، چون سیاه نمی‌تواند پیاده را نگه دارد.",
              "The Queen's Gambit: White offers the c-pawn to lure d5 away from the centre. Not a true gambit, since Black cannot keep the pawn."),
            M("e6", "سیاه نمی‌گیرد و d5 را محکم نگه می‌دارد: گامبی وزیرِ ردشده.",
              "Black declines and holds d5: the Queen's Gambit Declined."),
            M("Nc3", "فشار بیشتر روی d5.", "More pressure on d5."),
            M("Nf6", "دفاع از d5.", "Defending d5."),
            M("Bg5", "اسب f6، یکی از مدافع‌های d5، به وزیر میخ می‌شود.",
              "The f6 knight, a defender of d5, is pinned to the queen."),
            M("Be7", "سیاه میخ را باز می‌کند.", "Black breaks the pin."),
            M("e3", "راه فیل f1 باز می‌شود.", "The f1 bishop is freed."),
            M("O-O", "شاه سیاه امن است.", "Black's king is safe."),
            M("Nf3", "گسترش.", "Development."),
            M("Nbd7", "اسب به d7 می‌رود تا بعداً c5 یا e5 را پشتیبانی کند.",
              "The knight goes to d7 to back up ...c5 or ...e5 later."),
            M("Rc1", "رخ به ستون c می‌رود که بعد از تعویض‌ها باز خواهد شد.",
              "The rook goes to the c-file, which will open after exchanges."),
            M("c6", "d5 محکم‌تر می‌شود. سیاه منتظر لحظه‌ی مناسب برای آزاد کردن بازی است.",
              "d5 is reinforced. Black waits for the right moment to free the game."),
        ],
    },
    {
        "id": "slav", "group": "vs-d4", "side": "b",
        "name": {"fa": "دفاع اسلاو", "en": "Slav Defence"},
        "summary": {
            "fa": "به محکمی گامبی وزیرِ ردشده، ولی بدون فیل محبوس. یکی از قابل‌اعتمادترین دفاع‌های امروز.",
            "en": "As solid as the Queen's Gambit Declined, but without the shut-in bishop. One of today's most reliable defences.",
        },
        "ideas": {
            "fa": ["d5 با پیاده‌ی c محکم می‌شود و راه فیل c8 باز می‌ماند.",
                   "فیل c8 پیش از e6 به f5 می‌رود.",
                   "گرفتن پیاده‌ی c4 در لحظه‌ای که سفید نمی‌تواند راحت پسش بگیرد."],
            "en": ["d5 is backed by the c-pawn, leaving the c8 bishop free.",
                   "The c8 bishop goes to f5 before ...e6.",
                   "Taking on c4 when White cannot easily win it back."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("d5", "سیاه مرکز را پس نمی‌دهد.", "Black holds his share of the centre."),
            M("c4", "گامبی وزیر.", "The Queen's Gambit."),
            M("c6", "سیاه d5 را با پیاده‌ی c محکم می‌کند؛ راه فیل c8 باز می‌ماند.",
              "Black backs d5 with the c-pawn; the c8 bishop stays free."),
            M("Nf3", "گسترش.", "Development."),
            M("Nf6", "گسترش و دفاع از d5.", "Development, defending d5."),
            M("Nc3", "فشار روی d5.", "Pressure on d5."),
            M("dxc4", "حالا که c6 بازی شده، سیاه پیاده را می‌گیرد و تهدید می‌کند با b5 نگهش دارد.",
              "Now that ...c6 is in, Black takes the pawn and threatens to hold it with ...b5."),
            M("a4", "سفید جلوی b5 را می‌گیرد.", "White stops ...b5."),
            M("Bf5", "فیل آزادانه بیرون می‌آید.", "The bishop comes out freely."),
            M("e3", "سفید آماده‌ی پس گرفتن c4 است.", "White prepares to take back on c4."),
            M("e6", "راه فیل f8 باز می‌شود.", "The f8 bishop is freed."),
            M("Bxc4", "پیاده پس گرفته شد؛ سفید مرکز دارد و سیاه فیل‌های فعال.",
              "The pawn is back; White has the centre, Black has active bishops."),
            M("Bb4", "فیل فعال می‌شود و اسب c3 را میخ می‌کند، که پیشروی e4 را سخت می‌کند.",
              "The bishop becomes active and pins the c3 knight, making e4 harder."),
        ],
    },
    {
        "id": "kings-indian", "group": "vs-d4", "side": "b",
        "name": {"fa": "دفاع هندی شاه", "en": "King's Indian Defence"},
        "summary": {
            "fa": "دفاعی تهاجمی: سیاه مرکز را به سفید می‌دهد و بعد با e5 به آن ضربه می‌زند. گشایش محبوب فیشر و کاسپاروف.",
            "en": "An attacking defence: Black lets White have the centre, then strikes at it with ...e5. A favourite of Fischer and Kasparov.",
        },
        "ideas": {
            "fa": ["فیل فیانکتو روی g7 از دور به مرکز فشار می‌آورد.",
                   "ضربه به مرکز با e5.",
                   "وقتی مرکز بسته شد: سیاه با f5 در جناح شاه، سفید با c5 در جناح وزیر."],
            "en": ["The fianchettoed bishop on g7 presses on the centre from afar.",
                   "Striking at the centre with ...e5.",
                   "Once the centre closes: Black attacks with ...f5, White with c5."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("Nf6", "سیاه با اسب جلوی e4 را می‌گیرد و هنوز تصمیم نمی‌گیرد پیاده‌هایش کجا بروند.",
              "Black stops e4 with a piece and keeps his pawns flexible."),
            M("c4", "سفید در مرکز فضای بیشتری می‌گیرد.", "White gains more space in the centre."),
            M("g6", "آماده‌کردن فیانکتو: فیل از g7 روی قطر بلند به مرکز فشار خواهد آورد.",
              "Preparing a fianchetto: from g7 the bishop will press on the centre."),
            M("Nc3", "آماده‌کردن e4.", "Preparing e4."),
            M("Bg7", "فیل روی قطر بلند.", "The bishop on the long diagonal."),
            M("e4", "سفید مرکز بزرگی می‌سازد. سیاه عمداً اجازه داده تا بعداً به آن حمله کند.",
              "White builds a big centre. Black allowed it on purpose, planning to attack it."),
            M("d6", "e5 را آماده می‌کند.", "Preparing ...e5."),
            M("Nf3", "گسترش.", "Development."),
            M("O-O", "شاه پشت فیل g7 امن می‌شود.", "The king is safe behind the g7 bishop."),
            M("Be2", "گسترش آرام.", "Quiet development."),
            M("e5", "ضربه‌ی سیاه به مرکز.", "Black's strike at the centre."),
            M("O-O", "سفید هم قلعه می‌رود.", "White castles too."),
            M("Nc6", "فشار روی d4.", "Pressure on d4."),
            M("d5", "سفید مرکز را می‌بندد و با حمله به اسب c6 وقت می‌خرد.",
              "White closes the centre, gaining time on the c6 knight."),
            M("Ne7", "حالا بازی دو جناحه است: سفید با c5 در جناح وزیر، سیاه با f5 در جناح شاه به شاه سفید حمله می‌کند.",
              "Now the game splits: White attacks on the queenside with c5, Black goes for White's king with ...f5."),
        ],
    },
]


# Six more, added with the coach: a gambit, a hypermodern defence to 1.e4,
# a system for White, and three of the main defences to 1.d4.
LESSONS += [
    {
        "id": "kings-gambit", "group": "e4", "side": "w",
        "name": {"fa": "گامبی شاه", "en": "King's Gambit"},
        "summary": {
            "fa": "قدیمی‌ترین گامبی مشهور: سفید پیاده‌ی f را می‌دهد تا مرکز و ستون f را بگیرد. در این خط سیاه پیاده را پس می‌دهد و آرام گسترش می‌یابد.",
            "en": "The oldest famous gambit: White gives the f-pawn for the centre and the f-file. In this line Black gives the pawn back and develops calmly.",
        },
        "ideas": {
            "fa": ["f4 پیاده‌ی e5 را منحرف می‌کند تا سفید با d4 مرکز کامل بگیرد.",
                   "ستون f بعد از قلعه برای رخ سفید باز می‌شود.",
                   "برای سیاه: d5 سریع، به‌جای چسبیدن به پیاده‌ی اضافه."],
            "en": ["f4 deflects the e5 pawn so White can take the whole centre with d4.",
                   "After castling the f-file opens for White's rook.",
                   "For Black: a quick ...d5 rather than clinging to the extra pawn."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("e5", "سیاه هم همین کار را می‌کند.", "Black does the same."),
            M("f4", "گامبی شاه: پیاده‌ی f پیشنهاد می‌شود تا پیاده‌ی e5 از مرکز دور شود.",
              "The King's Gambit: the f-pawn is offered to lure the e5 pawn away from the centre."),
            M("exf4", "سیاه گامبی را می‌پذیرد و یک پیاده جلو می‌افتد.",
              "Black accepts and is a pawn up."),
            M("Nf3", "گسترش؛ جلوی کیش وزیر روی h4 را هم می‌گیرد.",
              "Development; it also stops ...Qh4+."),
            M("d5", "سیاه پیاده را پس می‌دهد تا مرکز را باز کند و راحت گسترش یابد: دفاع مدرن.",
              "Black gives the pawn back to open the centre and develop freely: the Modern Defence."),
            M("exd5", "سفید می‌گیرد.", "White takes."),
            M("Nf6", "سیاه با گسترش به پیاده‌ی d5 حمله می‌کند.",
              "Black develops with an attack on d5."),
            M("Bb5+", "کیش با فیل، تا گسترش سیاه را کمی به هم بزند.",
              "A bishop check, to disturb Black's development a little."),
            M("c6", "سیاه کیش را با پیاده می‌گیرد و پیاده‌ی d5 را هدف می‌گیرد.",
              "Black blocks with a pawn that also hits d5."),
            M("dxc6", "سفید پیاده را نگه نمی‌دارد و تعویض می‌کند.",
              "White does not try to keep the pawn and exchanges."),
            M("bxc6", "سیاه با پیاده پس می‌گیرد و ستون b نیمه‌باز می‌شود.",
              "Black recaptures with a pawn, and the b-file half-opens."),
            M("Bc4", "فیل به قطر خوبش برمی‌گردد و f7 را نشانه می‌گیرد.",
              "The bishop returns to its good diagonal, aiming at f7."),
            M("Nd5", "اسب در مرکز مستقر می‌شود و از پیاده‌ی f4 هم دفاع می‌کند. بازی متعادل و پرتحرک است.",
              "The knight settles in the centre and guards the f4 pawn too. The game is balanced and lively."),
        ],
    },
    {
        "id": "pirc", "group": "vs-e4", "side": "b",
        "name": {"fa": "دفاع پیرتس", "en": "Pirc Defence"},
        "summary": {
            "fa": "دفاعی نوین و منعطف: سیاه مرکز را به سفید می‌دهد، فیلش را فیانکتو می‌کند و بعداً با e5 یا c5 به مرکز ضربه می‌زند.",
            "en": "A modern, flexible defence: Black lets White have the centre, fianchettoes a bishop and strikes at the centre later with ...e5 or ...c5.",
        },
        "ideas": {
            "fa": ["فیل g7 از دور مرکز سفید را زیر فشار می‌گذارد.",
                   "ضربه به مرکز با e5 یا c5، وقتی سفید گسترش را تمام کرد.",
                   "فشار روی d4 با Bg4 و Nc6."],
            "en": ["The g7 bishop presses on White's centre from afar.",
                   "Strike at the centre with ...e5 or ...c5 once White has developed.",
                   "Pressure on d4 with ...Bg4 and ...Nc6."],
        },
        "moves": [
            M("e4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("d6", "سیاه یک پیاده‌ی کوتاه جلو می‌برد و خانه‌ی e5 را کنترل می‌کند.",
              "Black moves a pawn one square, covering e5."),
            M("d4", "سفید مرکز را کامل می‌گیرد.", "White takes the full centre."),
            M("Nf6", "حمله به e4 با گسترش.", "Developing with an attack on e4."),
            M("Nc3", "دفاع از e4.", "Defending e4."),
            M("g6", "آماده‌کردن فیانکتو: این همان ایده‌ی پیرتس است.",
              "Preparing the fianchetto: the idea of the Pirc."),
            M("Nf3", "گسترش آرام و محکم؛ این «سیستم کلاسیک» است.",
              "Quiet, solid development: the Classical System."),
            M("Bg7", "فیل روی قطر بلند به مرکز نگاه می‌کند.",
              "The bishop on the long diagonal looks at the centre."),
            M("Be2", "سفید آماده‌ی قلعه‌رفتن می‌شود.", "White prepares to castle."),
            M("O-O", "شاه سیاه امن است.", "Black's king is safe."),
            M("O-O", "سفید هم قلعه می‌رود.", "White castles too."),
            M("Bg4", "فیل اسب f3 را، که از d4 دفاع می‌کند، میخ می‌کند.",
              "The bishop pins the f3 knight, a defender of d4."),
            M("Be3", "سفید d4 را با فیل محکم می‌کند.", "White reinforces d4 with the bishop."),
            M("Nc6", "فشار دوباره روی d4؛ سیاه آماده‌ی e5 است.",
              "More pressure on d4; Black is ready for ...e5."),
        ],
    },
    {
        "id": "catalan", "group": "systems", "side": "w",
        "name": {"fa": "گشایش کاتالان", "en": "Catalan Opening"},
        "summary": {
            "fa": "گامبی وزیر با فیل فیانکتو روی g2: فشار بلندمدت روی قطر بلند و جناح وزیر سیاه. محبوب قهرمانان جهان از کرامنیک تا کارلسن.",
            "en": "A Queen's Gambit with the bishop fianchettoed on g2: long-term pressure on the long diagonal and Black's queenside. A world champions' favourite from Kramnik to Carlsen.",
        },
        "ideas": {
            "fa": ["فیل g2 روی قطر h1 تا a8 فشار دائمی می‌آورد.",
                   "اگر سیاه c4 را بگیرد، سفید با وزیر پسش می‌گیرد.",
                   "برای سیاه: گسترش فیل c8 و آزاد کردن بازی با c5."],
            "en": ["The g2 bishop presses constantly along the h1-a8 diagonal.",
                   "If Black takes on c4, White wins it back with the queen.",
                   "For Black: developing the c8 bishop and freeing the game with ...c5."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("Nf6", "سیاه جلوی e4 را می‌گیرد.", "Black stops e4."),
            M("c4", "فضای بیشتر در مرکز.", "More space in the centre."),
            M("e6", "راه فیل f8 باز می‌شود و d5 آماده می‌شود.", "Opens the f8 bishop and prepares ...d5."),
            M("g3", "حرکت شاخص کاتالان: آماده‌کردن فیانکتو.", "The Catalan move: preparing the fianchetto."),
            M("d5", "سیاه در مرکز جای پا می‌گیرد.", "Black takes a stake in the centre."),
            M("Bg2", "فیل روی قطر بلند؛ از دور به b7 و a8 نگاه می‌کند.",
              "The bishop on the long diagonal, eyeing b7 and a8 from afar."),
            M("Be7", "گسترش آرام و آماده‌ی قلعه.", "Quiet development, ready to castle."),
            M("Nf3", "گسترش.", "Development."),
            M("O-O", "شاه سیاه امن است.", "Black's king is safe."),
            M("O-O", "سفید هم قلعه می‌رود.", "White castles too."),
            M("dxc4", "کاتالانِ باز: سیاه پیاده را می‌گیرد تا فیل g2 را به دیوار پیاده‌ها بزند.",
              "The Open Catalan: Black takes the pawn, so the g2 bishop meets no pawn wall."),
            M("Qc2", "سفید آماده‌ی پس گرفتن c4 با وزیر است.", "White gets ready to take back on c4 with the queen."),
            M("a6", "سیاه آماده‌ی b5 است تا پیاده را نگه دارد.", "Black prepares ...b5 to hold the pawn."),
            M("Qxc4", "پیاده پس گرفته شد.", "The pawn is back."),
            M("b5", "سیاه با حمله به وزیر در جناح وزیر فضا می‌گیرد.",
              "Black gains queenside space with tempo on the queen."),
            M("Qc2", "وزیر عقب می‌رود و قطر c2 را زیر نظر دارد.", "The queen retreats, watching the c2-h7 diagonal."),
            M("Bb7", "فیل سیاه در برابر فیل g2 روی همان قطر قرار می‌گیرد. نبرد بر سر قطر بلند است.",
              "Black's bishop meets the g2 bishop on the same diagonal. The fight is for the long diagonal."),
        ],
    },
    {
        "id": "nimzo-indian", "group": "vs-d4", "side": "b",
        "name": {"fa": "دفاع نیمزو-هندی", "en": "Nimzo-Indian Defence"},
        "summary": {
            "fa": "یکی از بهترین دفاع‌ها در برابر d4: سیاه با میخ کردن اسب c3 برای خانه‌ی e4 می‌جنگد و حاضر است فیلش را با اسب عوض کند.",
            "en": "One of the best defences to 1.d4: Black fights for e4 by pinning the c3 knight, and is happy to trade the bishop for it.",
        },
        "ideas": {
            "fa": ["Bb4 اسب c3 را میخ می‌کند و کنترل e4 را از سفید می‌گیرد.",
                   "تعویض فیل با اسب، پیاده‌های دوبله‌ی c را برای سفید می‌سازد.",
                   "ضربه به مرکز با c5 و d5."],
            "en": ["...Bb4 pins the c3 knight and takes control of e4 away from White.",
                   "Trading the bishop for the knight gives White doubled c-pawns.",
                   "Strike at the centre with ...c5 and ...d5."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("Nf6", "سیاه جلوی e4 را می‌گیرد.", "Black stops e4."),
            M("c4", "فضای بیشتر.", "More space."),
            M("e6", "راه فیل f8 باز می‌شود.", "The f8 bishop is freed."),
            M("Nc3", "سفید e4 را آماده می‌کند.", "White prepares e4."),
            M("Bb4", "حرکت نیمزو: اسب c3 میخ می‌شود و e4 دیگر آسان نیست.",
              "The Nimzo move: the c3 knight is pinned, and e4 is no longer easy."),
            M("e3", "سیستم روبینشتاین: سفید آرام گسترش می‌یابد و فیل f1 را آزاد می‌کند.",
              "The Rubinstein System: White develops quietly and frees the f1 bishop."),
            M("O-O", "شاه سیاه امن است.", "Black's king is safe."),
            M("Bd3", "فیل رو به جناح شاه سیاه.", "The bishop aims at Black's kingside."),
            M("d5", "سیاه در مرکز جای پا می‌گیرد.", "Black takes a stake in the centre."),
            M("Nf3", "گسترش.", "Development."),
            M("c5", "ضربه به d4؛ سیاه مرکز سفید را به چالش می‌کشد.", "A strike at d4; Black challenges White's centre."),
            M("O-O", "سفید قلعه می‌رود.", "White castles."),
            M("Nc6", "فشار بیشتر روی d4. هر دو طرف گسترش یافته‌اند و نبرد مرکزی شروع می‌شود.",
              "More pressure on d4. Both sides are developed and the central fight begins."),
        ],
    },
    {
        "id": "grunfeld", "group": "vs-d4", "side": "b",
        "name": {"fa": "دفاع گرونفلد", "en": "Grünfeld Defence"},
        "summary": {
            "fa": "دفاعی پویا و مبارزه‌جو: سیاه اجازه می‌دهد سفید مرکز بزرگی بسازد و بعد با فیل g7 و c5 آن را زیر آتش می‌گیرد. محبوب کاسپاروف.",
            "en": "A dynamic, fighting defence: Black lets White build a big centre, then puts it under fire with the g7 bishop and ...c5. A Kasparov favourite.",
        },
        "ideas": {
            "fa": ["سیاه مرکز را به سفید می‌دهد تا بعد به آن حمله کند.",
                   "فیل g7 و پیاده‌ی c5 هر دو به d4 فشار می‌آورند.",
                   "اگر مرکز سفید سقوط کند، سیاه بازی را در دست دارد."],
            "en": ["Black gives White the centre in order to attack it.",
                   "The g7 bishop and the c5 pawn both press on d4.",
                   "If White's centre falls, Black takes over."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("Nf6", "سیاه جلوی e4 را می‌گیرد.", "Black stops e4."),
            M("c4", "فضای بیشتر.", "More space."),
            M("g6", "آماده‌کردن فیانکتو.", "Preparing the fianchetto."),
            M("Nc3", "آماده‌کردن e4.", "Preparing e4."),
            M("d5", "حرکت گرونفلد: سیاه برخلاف هندی شاه همین حالا در مرکز می‌جنگد.",
              "The Grünfeld move: unlike the King's Indian, Black fights in the centre at once."),
            M("cxd5", "سیستم تعویض: سفید تعویض می‌کند تا مرکز بزرگی بسازد.",
              "The Exchange Variation: White trades to build a big centre."),
            M("Nxd5", "اسب پس می‌گیرد.", "The knight recaptures."),
            M("e4", "سفید با حمله به اسب مرکز کامل را می‌گیرد.",
              "White takes the full centre, attacking the knight."),
            M("Nxc3", "سیاه اسب‌ها را عوض می‌کند.", "Black trades knights."),
            M("bxc3", "سفید مرکز بزرگی دارد: c3، d4 و e4.",
              "White has a big centre: c3, d4 and e4."),
            M("Bg7", "فیل روی قطر بلند، مستقیم به c3 و d4 نگاه می‌کند.",
              "The bishop on the long diagonal stares at c3 and d4."),
            M("Nf3", "گسترش و دفاع از d4.", "Development, defending d4."),
            M("c5", "ضربه‌ی کلاسیک گرونفلد به d4.", "The classical Grünfeld strike at d4."),
            M("Be2", "سفید آرام گسترش را تمام می‌کند.", "White finishes developing quietly."),
            M("O-O", "شاه سیاه امن است. نبرد بر سر مرکز سفید است: آیا دوام می‌آورد یا سقوط می‌کند؟",
              "Black's king is safe. The fight is over White's centre: will it hold or fall?"),
        ],
    },
    {
        "id": "dutch", "group": "vs-d4", "side": "b",
        "name": {"fa": "دفاع هلندی: لنینگراد", "en": "Dutch Defence: Leningrad"},
        "summary": {
            "fa": "سیاه با f5 از همان حرکت اول برای خانه‌ی e4 می‌جنگد و بازی نامتقارنی می‌سازد. در سیستم لنینگراد، فیل روی g7 فیانکتو می‌شود.",
            "en": "Black fights for e4 with ...f5 from the first move and makes the game unbalanced. In the Leningrad System the bishop is fianchettoed on g7.",
        },
        "ideas": {
            "fa": ["f5 خانه‌ی e4 را کنترل می‌کند.",
                   "فیل g7 و پیاده‌ی f5 با هم برای حمله در جناح شاه آماده می‌شوند.",
                   "نقشه‌ی سیاه: e5 با کمک Qe8 یا Nc6."],
            "en": ["...f5 controls e4.",
                   "The g7 bishop and the f5 pawn work together towards a kingside attack.",
                   "Black's plan: ...e5, with the help of ...Qe8 or ...Nc6."],
        },
        "moves": [
            M("d4", "سفید مرکز را می‌گیرد.", "White takes the centre."),
            M("f5", "دفاع هلندی: سیاه با پیاده‌ی f خانه‌ی e4 را می‌گیرد.",
              "The Dutch: Black takes e4 with the f-pawn."),
            M("g3", "سفید فیلش را فیانکتو می‌کند تا به قطر بلند و e4 فشار بیاورد.",
              "White fianchettoes to press on the long diagonal and e4."),
            M("Nf6", "گسترش و کنترل e4.", "Development and control of e4."),
            M("Bg2", "فیل روی قطر بلند.", "The bishop on the long diagonal."),
            M("g6", "سیستم لنینگراد: سیاه هم فیلش را فیانکتو می‌کند.",
              "The Leningrad System: Black fianchettoes too."),
            M("Nf3", "گسترش.", "Development."),
            M("Bg7", "فیل روی قطر بلند.", "The bishop on the long diagonal."),
            M("O-O", "سفید قلعه می‌رود.", "White castles."),
            M("O-O", "سیاه هم قلعه می‌رود.", "Black castles too."),
            M("c4", "سفید فضای بیشتری در مرکز می‌گیرد.", "White gains more central space."),
            M("d6", "آماده‌کردن e5.", "Preparing ...e5."),
            M("Nc3", "گسترش و کنترل e4.", "Development and control of e4."),
            M("Qe8", "وزیر از e8 از e5 پشتیبانی می‌کند و بعداً می‌تواند به h5 برود و به شاه سفید حمله کند.",
              "From e8 the queen backs up ...e5, and can later swing to h5 against White's king."),
        ],
    },
]


def load_table():
    """Opening names by position (pieces, side to move, castling), as the engine keys them."""
    names = {}
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        eco, name, fa, uci = line.split("\t")
        b = chess.Board()
        for m in uci.split():
            b.push_uci(m)
        names.setdefault(" ".join(b.fen().split()[:3]), (eco, name, fa))
    return names


def main():
    names = load_table()
    groups = {g["id"] for g in GROUPS}
    out = []
    for L in LESSONS:
        assert L["group"] in groups, L["id"]
        assert L["side"] in ("w", "b"), L["id"]
        b = chess.Board()
        last_named = None
        moves = []
        for i, m in enumerate(L["moves"]):
            try:
                move = b.parse_san(m["san"])
            except ValueError as e:
                sys.exit(f"{L['id']}: move {i + 1} ({m['san']}) is not legal: {e}")
            san = b.san(move)
            if san.rstrip("+#") != m["san"].rstrip("+#"):
                sys.exit(f"{L['id']}: move {i + 1} written {m['san']}, SAN is {san}")
            b.push(move)
            found = names.get(" ".join(b.fen().split()[:3]))
            if found:
                last_named = found
            moves.append({"uci": move.uci(), "san": san, "fa": m["fa"], "en": m["en"]})
        if not last_named:
            sys.exit(f"{L['id']}: the line never reaches a named position")
        out.append({**{k: L[k] for k in ("id", "group", "side", "name", "summary", "ideas")},
                    "eco": last_named[0], "tableName": last_named[1], "moves": moves})
        print(f"{L['id']:18} {len(moves):2} plies  {last_named[0]} {last_named[1]}")

    OUT.write_text(json.dumps({"groups": GROUPS, "lessons": out}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {len(out)} lessons to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
