package ir.simorgh.chess

import java.util.Calendar

/**
 * PGN in and out, the same as the desktop app's pgn.ts. Writing is plain
 * formatting. Reading only extracts the moves as written; which move each
 * one is, and whether it is legal at all, the engine decides from its `san`
 * list for each position, so this app still implements no chess rules.
 *
 * Every brace and bracket in the patterns below is escaped, even where
 * desktop Java would let it pass: Android compiles regexes with ICU, which
 * rejects an unescaped `}` -- the first version of this file crashed on
 * import because of exactly that.
 */
object Pgn {

    class Info(
        val sans: List<String>,
        val white: String,
        val black: String,
        val result: String,          // "1-0", "0-1", "1/2-1/2" or "*"
        val eco: String? = null,
        val opening: String? = null,
        val timeControl: String? = null,
    )

    private fun tag(name: String, value: String) =
        "[$name \"${value.replace("\\", "\\\\").replace("\"", "\\\"")}\"]"

    fun write(g: Info): String {
        val c = Calendar.getInstance()
        val date = "%04d.%02d.%02d".format(c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH))
        val tags = mutableListOf(
            tag("Event", "Simorgh game"), tag("Site", "Simorgh"), tag("Date", date), tag("Round", "-"),
            tag("White", g.white), tag("Black", g.black), tag("Result", g.result),
        )
        g.eco?.let { tags += tag("ECO", it) }
        g.opening?.let { tags += tag("Opening", it) }
        g.timeControl?.let { tags += tag("TimeControl", it) }

        // Movetext, wrapped at 80 columns as the PGN standard asks.
        val words = mutableListOf<String>()
        g.sans.forEachIndexed { i, san ->
            if (i % 2 == 0) words += "${i / 2 + 1}."
            words += san
        }
        words += g.result
        val lines = mutableListOf<String>()
        var line = ""
        for (w in words) {
            line = when {
                line.isEmpty() -> w
                line.length + 1 + w.length > 80 -> { lines += line; w }
                else -> "$line $w"
            }
        }
        if (line.isNotEmpty()) lines += line
        return tags.joinToString("\n") + "\n\n" + lines.joinToString("\n") + "\n"
    }

    sealed class Read {
        class Moves(val sans: List<String>) : Read()
        object SetUp : Read()   // starts from a set-up position
        object Empty : Read()
    }

    /** The moves of the first game in `text`, as written. */
    fun readMoves(text: String): Read {
        if (Regex("""\[\s*SetUp\s+"1"\s*\]""", RegexOption.IGNORE_CASE).containsMatchIn(text) ||
            Regex("""\[\s*FEN\s+"""", RegexOption.IGNORE_CASE).containsMatchIn(text)) return Read.SetUp

        var body = text.lines()
            .filterNot { Regex("""^\s*\[.*\]\s*$""").matches(it) }   // tag pairs
            .joinToString(" ") { it.replace(Regex(";.*$"), "") }   // rest-of-line comments
            .replace(Regex("""\{[^\}]*\}"""), " ")                    // brace comments
            .replace(Regex("""\$\d+"""), " ")                       // annotation glyphs

        // Variations nest, so strip them with a depth count, not a regex.
        val flat = StringBuilder()
        var depth = 0
        for (ch in body) when {
            ch == '(' -> depth++
            ch == ')' -> depth = maxOf(0, depth - 1)
            depth == 0 -> flat.append(ch)
        }
        body = flat.toString()

        val sans = mutableListOf<String>()
        for (raw in body.split(Regex("\\s+"))) {
            val tok = raw.replace(Regex("""^\d+\.+"""), "")
            if (tok.isEmpty()) continue
            if (Regex("""^(1-0|0-1|1/2-1/2|\*)$""").matches(tok)) break
            sans += tok
        }
        return if (sans.isEmpty()) Read.Empty else Read.Moves(sans)
    }

    /** One form for "Nf3+", "Nf3!?", "0-0", "e8Q" and "e8=Q" alike. */
    fun normalize(san: String): String = san
        .replace(Regex("[+#!?]+$"), "")
        .replace(Regex("e\\.p\\.$"), "")
        .replace(Regex("^0-0-0"), "O-O-O")
        .replace(Regex("^0-0"), "O-O")
        .replace(Regex("([a-h][18])([QRBN])$"), "$1=$2")
}
