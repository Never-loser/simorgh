"""Builds data/openings.tsv, the table the engine names openings from.

The names come from lichess-org/chess-openings (CC0): about 3,800 lines,
each an ECO code, a name like "Sicilian Defense: Najdorf Variation" and the
moves in SAN. This script replays each line to UCI -- the engine then needs
no SAN parser, only the move matching it already does for `position` -- and
adds the Persian name of the opening's family (the part before the colon).
Variation names stay in English; they are mostly people and places.

    python python/openings.py                 # fetch from GitHub
    python python/openings.py path/to/tsvs    # or use a local copy

Needs python-chess (pip install chess), for the SAN only.
"""

import sys
import urllib.request
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "openings.tsv"
URL = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/{}.tsv"

# Persian names of every family in the table. The build stops if the table
# gains one that is not here, rather than silently showing English.
FA = {
    "Alekhine Defense": "دفاع آلخین",
    "Amar Opening": "گشایش آمار",
    "Amazon Attack": "حمله‌ی آمازون",
    "Amsterdam Attack": "حمله‌ی آمستردام",
    "Anderssen's Opening": "گشایش اندرسن",
    "Australian Defense": "دفاع استرالیایی",
    "Barnes Defense": "دفاع بارنز",
    "Barnes Opening": "گشایش بارنز",
    "Basque Opening": "گشایش باسک",
    "Benko Gambit": "گامبی بنکو",
    "Benko Gambit Accepted": "گامبی بنکوی پذیرفته",
    "Benko Gambit Declined": "گامبی بنکوی ردشده",
    "Benoni Defense": "دفاع بنونی",
    "Bird Opening": "گشایش برد",
    "Bishop's Opening": "گشایش فیل",
    "Blackmar-Diemer Gambit": "گامبی بلکمار-دیمر",
    "Blackmar-Diemer Gambit Accepted": "گامبی بلکمار-دیمرِ پذیرفته",
    "Blackmar-Diemer Gambit Declined": "گامبی بلکمار-دیمرِ ردشده",
    "Blumenfeld Countergambit": "ضدگامبی بلومنفلد",
    "Blumenfeld Countergambit Accepted": "ضدگامبی بلومنفلدِ پذیرفته",
    "Bogo-Indian Defense": "دفاع بوگو-هندی",
    "Bongcloud Attack": "حمله‌ی بانگ‌کلاد",
    "Borg Defense": "دفاع بورگ",
    "Canard Opening": "گشایش کانار",
    "Caro-Kann Defense": "دفاع کاروکان",
    "Carr Defense": "دفاع کار",
    "Catalan Opening": "گشایش کاتالان",
    "Center Game": "بازی مرکز",
    "Center Game Accepted": "بازی مرکزِ پذیرفته",
    "Clemenz Opening": "گشایش کلمنز",
    "Colle System": "سیستم کوله",
    "Creepy Crawly Formation": "آرایش خزنده",
    "Czech Defense": "دفاع چک",
    "Danish Gambit": "گامبی دانمارکی",
    "Danish Gambit Accepted": "گامبی دانمارکیِ پذیرفته",
    "Danish Gambit Declined": "گامبی دانمارکیِ ردشده",
    "Dresden Opening": "گشایش درسدن",
    "Duras Gambit": "گامبی دوراس",
    "Dutch Defense": "دفاع هلندی",
    "Döry Defense": "دفاع دوری",
    "East Indian Defense": "دفاع هندی شرقی",
    # Not "گامبی فیل": فیل is the bishop.
    "Elephant Gambit": "گامبی الفنت",
    "English Defense": "دفاع انگلیسی",
    "English Opening": "گشایش انگلیسی",
    "English Orangutan": "اورانگوتان انگلیسی",
    "Englund Gambit": "گامبی انگلوند",
    "Englund Gambit Declined": "گامبی انگلوندِ ردشده",
    "Formation": "آرایش",
    "Four Knights Game": "بازی چهار اسب",
    "French Defense": "دفاع فرانسوی",
    "Fried Fox Defense": "دفاع فرایدفاکس",
    "Global Opening": "گشایش گلوبال",
    "Goldsmith Defense": "دفاع گلداسمیت",
    "Grob Opening": "گشایش گروب",
    "Grünfeld Defense": "دفاع گرونفلد",
    "Gunderam Defense": "دفاع گوندرام",
    "Hippopotamus Defense": "دفاع اسب‌آبی",
    "Horwitz Defense": "دفاع هورویتس",
    "Hungarian Opening": "گشایش مجاری",
    "Indian Defense": "دفاع هندی",
    "Irish Gambit": "گامبی ایرلندی",
    "Italian Game": "بازی ایتالیایی",
    "Kangaroo Defense": "دفاع کانگورو",
    "King's Gambit": "گامبی شاه",
    "King's Gambit Accepted": "گامبی شاهِ پذیرفته",
    "King's Gambit Declined": "گامبی شاهِ ردشده",
    "King's Indian Attack": "حمله‌ی هندی شاه",
    "King's Indian Attack, with Bf5": "حمله‌ی هندی شاه، با Bf5",
    "King's Indian Attack, with e6": "حمله‌ی هندی شاه، با e6",
    "King's Indian Defense": "دفاع هندی شاه",
    "King's Knight Opening": "گشایش اسب شاه",
    "King's Pawn Game": "بازی پیاده‌ی شاه",
    "King's Pawn Opening": "گشایش پیاده‌ی شاه",
    "Kádas Opening": "گشایش کاداش",
    "Lasker Simul Special": "ویژه‌ی سیمولتانه‌ی لاسکر",
    "Latvian Gambit": "گامبی لتونیایی",
    "Latvian Gambit Accepted": "گامبی لتونیاییِ پذیرفته",
    "Lemming Defense": "دفاع لمینگ",
    "Lion Defense": "دفاع شیر",
    "London System": "سیستم لندن",
    "London System, with Bd3": "سیستم لندن، با Bd3",
    "London System, with Be2": "سیستم لندن، با Be2",
    "Marienbad System": "سیستم ماریین‌باد",
    "Mexican Defense": "دفاع مکزیکی",
    "Mieses Opening": "گشایش میزس",
    "Mikenas Defense": "دفاع میکناس",
    "Modern Defense": "دفاع مدرن",
    "Montevideo Defense": "دفاع مونته‌ویدئو",
    "Neo-Grünfeld Defense": "دفاع نئوگرونفلد",
    "Nimzo-Indian Defense": "دفاع نیمزو-هندی",
    "Nimzo-Larsen Attack": "حمله‌ی نیمزو-لارسن",
    "Nimzowitsch Defense": "دفاع نیمزوویچ",
    "Old Indian Defense": "دفاع هندی قدیمی",
    "Owen Defense": "دفاع اوون",
    "Paleface Attack": "حمله‌ی رنگ‌پریده",
    "Petrov's Defense": "دفاع پتروف",
    "Philidor Defense": "دفاع فیلیدور",
    "Pirc Defense": "دفاع پیرتس",
    "Polish Defense": "دفاع لهستانی",
    "Polish Opening": "گشایش لهستانی",
    "Polish Opening, with d5": "گشایش لهستانی، با d5",
    "Ponziani Opening": "گشایش پونزیانی",
    "Portuguese Opening": "گشایش پرتغالی",
    "Pseudo Queen's Indian Defense": "دفاع شبه‌هندی وزیر",
    "Pterodactyl Defense": "دفاع پتروداکتیل",
    "Queen's Gambit": "گامبی وزیر",
    "Queen's Gambit Accepted": "گامبی وزیرِ پذیرفته",
    "Queen's Gambit Declined": "گامبی وزیرِ ردشده",
    "Queen's Indian Accelerated": "هندی وزیرِ سریع",
    "Queen's Indian Defense": "دفاع هندی وزیر",
    "Queen's Indian Defense, with e3": "دفاع هندی وزیر، با e3",
    "Queen's Indian Defense, with e3, Bb4+ Line": "دفاع هندی وزیر، با e3، خط Bb4+",
    "Queen's Pawn Game": "بازی پیاده‌ی وزیر",
    "Queen's Pawn, Mengarini Attack": "پیاده‌ی وزیر، حمله‌ی منگارینی",
    "Rapport-Jobava System": "سیستم راپورت-جوباوا",
    "Rapport-Jobava System, with e6": "سیستم راپورت-جوباوا، با e6",
    "Rat Defense": "دفاع موش",
    "Richter-Veresov Attack": "حمله‌ی ریشتر-ورسوف",
    "Robatsch Defense": "دفاع روباچ",
    "Rubinstein Opening": "گشایش روبینشتاین",
    "Ruy Lopez": "روی لوپز",
    "Réti Opening": "گشایش رتی",
    "Saragossa Opening": "گشایش ساراگوسا",
    "Scandinavian Defense": "دفاع اسکاندیناوی",
    "Scotch Game": "بازی اسکاتلندی",
    "Semi-Slav Defense": "دفاع نیمه‌اسلاو",
    "Semi-Slav Defense Accepted": "دفاع نیمه‌اسلاوِ پذیرفته",
    "Sicilian Defense": "دفاع سیسیلی",
    "Slav Defense": "دفاع اسلاو",
    "Slav Indian": "هندی اسلاو",
    "Sodium Attack": "حمله‌ی سدیم",
    "St. George Defense": "دفاع سنت جورج",
    "Tarrasch Defense": "دفاع تاراش",
    "Three Knights Opening": "گشایش سه اسب",
    "Torre Attack": "حمله‌ی توره",
    "Trompowsky Attack": "حمله‌ی ترومپوفسکی",
    "Valencia Opening": "گشایش والنسیا",
    "Van Geet Opening": "گشایش فان گیت",
    "Van't Kruijs Opening": "گشایش فانت کرویس",
    "Vienna Gambit, with Max Lange Defense": "گامبی وین، با دفاع ماکس لانگه",
    "Vienna Game": "بازی وین",
    "Vulture Defense": "دفاع کرکس",
    "Wade Defense": "دفاع وید",
    "Ware Defense": "دفاع ویر",
    "Ware Opening": "گشایش ویر",
    "Yusupov-Rubinstein System": "سیستم یوسوپوف-روبینشتاین",
    "Zaire Defense": "دفاع زئیر",
    "Zukertort Defense": "دفاع زوکرتورت",
    "Zukertort Opening": "گشایش زوکرتورت",
}


def read_source(src):
    rows = []
    for part in "abcde":
        if src:
            text = (Path(src) / f"{part}.tsv").read_text(encoding="utf-8")
        else:
            with urllib.request.urlopen(URL.format(part), timeout=60) as r:
                text = r.read().decode("utf-8")
        lines = text.splitlines()
        assert lines[0].split("\t")[:3] == ["eco", "name", "pgn"], lines[0]
        rows += [l.split("\t")[:3] for l in lines[1:] if l.strip()]
    return rows


def to_uci(pgn):
    board = chess.Board()
    out = []
    for tok in pgn.split():
        if tok[0].isdigit():  # move numbers: "1." or "1..."
            continue
        move = board.parse_san(tok)
        out.append(move.uci())
        board.push(move)
    return out


def main():
    rows = read_source(sys.argv[1] if len(sys.argv) > 1 else None)
    missing = sorted({n.split(":")[0] for _, n, _ in rows} - FA.keys())
    if missing:
        sys.exit("no Persian name for: " + ", ".join(missing))

    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Opening names, from lichess-org/chess-openings (CC0), with\n"
                "# Persian family names added. Built by python/openings.py.\n"
                "# eco<TAB>name<TAB>persian family<TAB>moves in UCI\n")
        for eco, name, pgn in rows:
            f.write(f"{eco}\t{name}\t{FA[name.split(':')[0]]}\t{' '.join(to_uci(pgn))}\n")
    print(f"wrote {len(rows)} openings to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
