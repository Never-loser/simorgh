package ir.simorgh.chess

/**
 * Every user-facing string, in both languages. The wording is the desktop
 * app's, key for key, so the two say the same thing about the same game.
 */
enum class Lang { FA, EN }

class Strings(val lang: Lang) {
    private val fa = lang == Lang.FA
    private fun t(faText: String, enText: String) = if (fa) faText else enText

    val appTitle get() = t("سیمرغ", "Simorgh")
    val subtitle get() = t("موتور شطرنجی که ارزیابی‌اش را توضیح می‌دهد", "the chess engine that explains its evaluation")
    val newGame get() = t("بازی جدید", "New game")
    val playAs get() = t("بازی با", "Play as")
    val white get() = t("سفید", "White")
    val black get() = t("سیاه", "Black")
    val strength get() = t("قدرت حریف", "Opponent strength")
    val thinkTime get() = t("زمان فکر", "Thinking time")
    val thinkHint get() = t(
        "پله‌ها نامساوی‌اند چون عمق با زمان خطی بالا نمی‌رود. عددها روی همین گوشی اندازه گرفته شده‌اند.",
        "The steps are uneven because depth does not grow linearly with time. The numbers were measured on a phone.",
    )
    val undo get() = t("برگشت", "Undo")
    val flip get() = t("چرخاندن تخته", "Flip board")
    val settings get() = t("تنظیمات", "Settings")
    val theme get() = t("تم", "Theme")
    val langToggle get() = t("English", "فارسی")
    val thinking get() = t("در حال فکر کردن…", "Thinking…")
    val yourMove get() = t("نوبت شماست", "Your move")
    val engineMove get() = t("نوبت موتور", "Engine to move")
    val checkmate get() = t("مات", "Checkmate")
    val stalemate get() = t("پات", "Stalemate")
    val check get() = t("کیش", "Check")
    val draw get() = t("مساوی", "Draw")
    val drawFifty get() = t("مساوی — قانون پنجاه حرکت", "Draw — fifty-move rule")
    val whiteWins get() = t("سفید برد", "White wins")
    val blackWins get() = t("سیاه برد", "Black wins")
    val evaluation get() = t("چرا این ارزیابی؟", "Why this evaluation?")
    val explorer get() = t("کاوشگر گشایش", "Opening explorer")
    val explorerHint get() = t(
        "حرکت‌هایی که کتاب موتور اینجا می‌شناسد و نتیجه‌ی بازی‌هایشان. روی حرکت بزنید تا بازی شود.",
        "The moves the engine's book knows here, and how their games ended. Tap one to play it.",
    )
    val noBook get() = t(
        "کتاب برای این وضعیت حرکتی نمی‌شناسد؛ از اینجا موتور خودش فکر می‌کند.",
        "The book knows no moves here; from now on the engine thinks for itself.",
    )
    val games get() = t("بازی", "games")
    val startPos get() = t("وضعیت شروع", "Starting position")
    val noOpening get() = t("هنوز گشایش نام‌داری نیست", "No named opening yet")
    val lessons get() = t("درس گشایش", "Lessons")
    val backToGame get() = t("بازی", "Play")
    val allLessons get() = t("همه‌ی درس‌ها", "All lessons")
    val keyIdeas get() = t("ایده‌های کلیدی", "Key ideas")
    val lessonAsWhite get() = t("در این درس شما سفید هستید.", "In this lesson you play White.")
    val lessonAsBlack get() = t("در این درس شما سیاه هستید.", "In this lesson you play Black.")
    val engineSees get() = t("این حرکت از نگاه موتور", "What the engine sees in this move")
    val noChange get() = t(
        "ارزیابی تقریباً تغییری نکرد؛ ارزش این حرکت در نقشه‌ی بعدی است، نه در عدد.",
        "The evaluation hardly moved: this move's value is in the plan that follows, not in the number.",
    )
    val evaluation2 get() = t("ارزیابی", "Evaluation")
    val deltaLegend get() = t("مثبت یعنی به سود سفید، منفی یعنی به سود سیاه.", "Positive favours White, negative favours Black.")
    val lessonStart get() = t(
        "با دکمه‌ی ▶ خط اصلی را حرکت به حرکت جلو ببرید. زیر هر حرکت توضیح آن و نگاه موتور به آن می‌آید.",
        "Step through the main line with ▶. Each move comes with what it is for and how the engine sees it.",
    )
    val continueVsEngine get() = t("ادامه با موتور از همین‌جا", "Continue against the engine from here")
    val practice get() = t("تمرین این درس", "Practise this lesson")
    val mistakesLabel get() = t("اشتباه", "mistakes")
    val restart get() = t("از اول", "Restart")
    val endPractice get() = t("پایان تمرین", "End practice")
    val findMove get() = t("نوبت شماست: حرکت بعدی خط اصلی را روی صفحه بازی کنید.", "Your move: play the next move of the main line on the board.")
    val correct get() = t("درسته!", "Right!")
    val opponentMoves get() = t("حریف حرکت می‌کند…", "The opponent is moving…")
    val wrong1 get() = t("این حرکت خط اصلی نیست. راهنمایی: مهره‌ی روشن‌شده را حرکت بدهید.", "That is not the main line. Hint: move the highlighted piece.")
    val wrong2a get() = t("حرکت درست", "The move is")
    val wrong2b get() = t(" است؛ خودتان آن را روی صفحه بازی کنید.", "; play it on the board yourself.")
    val lineDone get() = t("خط تمام شد!", "Line complete!")
    val perfect get() = t("بدون حتی یک اشتباه. آفرین!", "Not a single mistake. Well done!")
    val withMistakes get() = t("با {n} اشتباه. یک بار دیگر امتحان کنید تا بی‌نقص شود.", "With {n} mistakes. Try once more for a clean run.")
    val again get() = t("یک بار دیگر", "Once more")
    val timeControl get() = t("زمان", "Time control")
    val youFlagged get() = t("زمان شما تمام شد — موتور برد", "Your time ran out — the engine wins")
    val engineFlagged get() = t("زمان موتور تمام شد — شما بردید", "The engine's time ran out — you win")
    val pgnShare get() = t("اشتراک PGN", "Share PGN")
    val pgnPaste get() = t("وارد کردن از کلیپ‌بورد", "Paste from clipboard")
    val pgnLoaded get() = t("بازی وارد شد؛ از همین‌جا ادامه بدهید", "Game loaded; carry on from here")
    val clipboardEmpty get() = t("کلیپ‌بورد خالی است؛ اول PGN یک بازی را کپی کنید.", "The clipboard is empty; copy a game's PGN first.")
    val pgnSetup get() = t(
        "این بازی از یک وضعیت دلخواه شروع شده؛ فقط بازی‌هایی که از وضعیت شروع آغاز می‌شوند پشتیبانی می‌شوند.",
        "This game starts from a set-up position; only games from the initial position are supported.",
    )
    val pgnEmpty get() = t("حرکتی در متن کلیپ‌بورد پیدا نشد.", "No moves found in the clipboard text.")
    val pgnBadMove get() = t("حرکت {n} {move} در آن وضعیت قانونی نیست.", "Move {n} {move} is not legal in that position.")
    val coachTitle get() = t("مربی", "Coach")
    val on get() = t("روشن", "On")
    val off get() = t("خاموش", "Off")
    val coachEmpty get() = t("بعد از هر حرکت شما، مربی می‌گوید آن حرکت چقدر خوب بود، بهترش چه بود و چرا.",
                             "After each of your moves the coach says how good it was, what was better, and why.")
    val coachThinking get() = t("مربی در حال سنجیدن حرکت شما…", "The coach is judging your move…")
    val coachLoss get() = t("از شانس بردتان کم شد", "Win chance given away")
    val coachBetter get() = t("بهتر بود", "Better was")
    val coachReply get() = t("جواب موتور", "Engine's reply")
    val coachWhy get() = t("چرا بدتر است، نسبت به بهترین خط", "Why it is worse than the best line")
    val coachBestNote get() = t("همان حرکتی که موتور هم انتخاب می‌کرد.", "The move the engine would have played too.")
    val coachNoReason get() = t("فرق این دو خط در عمق محاسبه است، نه در یکی از جمله‌های ارزیابی.",
                                "The two lines differ in calculation, not in any one evaluation term.")
    val verdictBest get() = t("بهترین حرکت", "Best move")
    val verdictGood get() = t("حرکت خوب", "Good move")
    val verdictInaccuracy get() = t("نادقیق", "Inaccuracy")
    val verdictMistake get() = t("اشتباه", "Mistake")
    val verdictBlunder get() = t("اشتباه بزرگ", "Blunder")
    val reviewGame get() = t("مرور بازی", "Review game")
    val reviewTitle get() = t("مرور بازی", "Game review")
    val reviewClose get() = t("بازگشت", "Back")
    val reviewRunning get() = t("سنجیدن حرکت‌ها…", "Judging the moves…")
    val reviewOffer get() = t("بازی تمام شد — مرورش کنیم؟", "Game over — review it?")
    val accuracy get() = t("دقت", "Accuracy")
    val evalHint get() = t(
        "جمع همه‌ی جمله‌ها دقیقاً همان عددی است که موتور روی آن حساب می‌کند.",
        "Every term sums to exactly the number the engine searched on.",
    )
    val total get() = t("جمع کل", "Total")
    val engineScore get() = t("امتیاز موتور", "Engine score")
    val matches get() = t("مطابقت دارد", "matches")
    val mismatch get() = t("مطابقت ندارد", "does not match")
    val moves get() = t("حرکت‌ها", "Moves")
    val noMoves get() = t("هنوز حرکتی نشده", "No moves yet")
    val favoursWhite get() = t("به سود سفید", "favours White")
    val favoursBlack get() = t("به سود سیاه", "favours Black")
    val balanced get() = t("متعادل", "balanced")
    val connecting get() = t("در حال اتصال به موتور…", "Connecting to engine…")
    val noEngine get() = t("موتور در دسترس نیست", "Engine unavailable")
    val promote get() = t("به چه مهره‌ای ارتقا یابد؟", "Promote to?")
    val depth get() = t("عمق", "depth")
    val max get() = t("بی‌نهایت", "MAX")
    val learned get() = t("بازی به کتاب اضافه شد", "Game added to the book")

    fun term(name: String): String = (if (fa) TERMS_FA else TERMS_EN)[name] ?: name

    /** "wa2 wh2 bf7" -> readable, grouped by colour; "6v1" -> a count comparison. */
    fun detail(raw: String): String {
        if (raw.isBlank()) return ""
        Regex("""^(\d+)v(\d+)$""").find(raw)?.let { m ->
            return if (fa) "${m.groupValues[1]} در برابر ${m.groupValues[2]}"
                   else "${m.groupValues[1]} v ${m.groupValues[2]}"
        }
        val w = mutableListOf<String>(); val b = mutableListOf<String>()
        for (tok in raw.split(" ").filter { it.isNotBlank() }) {
            when {
                tok == "white" -> w += ""
                tok == "black" -> b += ""
                tok.startsWith("w") -> w += tok.drop(1)
                tok.startsWith("b") -> b += tok.drop(1)
            }
        }
        fun side(name: String, xs: List<String>): String {
            val named = xs.filter { it.isNotBlank() }
            // No colon between a word and Latin square names: it is its own
            // directional run and jumps to the wrong side of them in Persian.
            return if (named.isEmpty()) name else "$name ${named.joinToString(" ")}"
        }
        return listOfNotNull(
            w.takeIf { it.isNotEmpty() }?.let { side(white, it) },
            b.takeIf { it.isNotEmpty() }?.let { side(black, it) },
        ).joinToString(" / ")
    }

    companion object {
        val TERMS_FA = mapOf(
            "material.pawn" to "برتری پیاده", "material.knight" to "برتری اسب",
            "material.bishop" to "برتری فیل", "material.rook" to "برتری رخ",
            "material.queen" to "برتری وزیر",
            "placement.pawn" to "جای‌گیری پیاده‌ها", "placement.knight" to "جای‌گیری اسب‌ها",
            "placement.bishop" to "جای‌گیری فیل‌ها", "placement.rook" to "جای‌گیری رخ‌ها",
            "placement.queen" to "جای‌گیری وزیر",
            "king.placement" to "موقعیت شاه",
            "pawns.passed" to "پیاده گذشته", "pawns.isolated" to "پیاده منزوی",
            "pawns.doubled" to "پیاده دوتایی",
            "bishop.pair" to "جفت فیل",
            "mobility.knight" to "تحرک اسب‌ها",
            "mobility.bishop" to "تحرک فیل‌ها",
            "mobility.rook" to "تحرک رخ‌ها",
            "mobility.queen" to "تحرک وزیر",
            "king.shield" to "سپر پیاده‌ای شاه",
            "king.attack" to "حمله به شاه",
            "rounding" to "گِردکردن",
        )
        val TERMS_EN = mapOf(
            "material.pawn" to "pawn material", "material.knight" to "knight material",
            "material.bishop" to "bishop material", "material.rook" to "rook material",
            "material.queen" to "queen material",
            "placement.pawn" to "pawn placement", "placement.knight" to "knight placement",
            "placement.bishop" to "bishop placement", "placement.rook" to "rook placement",
            "placement.queen" to "queen placement",
            "king.placement" to "king placement",
            "pawns.passed" to "passed pawns", "pawns.isolated" to "isolated pawns",
            "pawns.doubled" to "doubled pawns",
            "bishop.pair" to "bishop pair",
            "mobility.knight" to "knight mobility",
            "mobility.bishop" to "bishop mobility",
            "mobility.rook" to "rook mobility",
            "mobility.queen" to "queen mobility",
            "king.shield" to "king's pawn shield",
            "king.attack" to "attack on the king",
            "rounding" to "rounding",
        )
    }
}
