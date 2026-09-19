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
            "rounding" to "rounding",
        )
    }
}
