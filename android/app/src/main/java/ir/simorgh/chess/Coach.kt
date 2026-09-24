package ir.simorgh.chess

import kotlin.math.exp

/**
 * The coach, the same as the desktop app's coach.ts: a move is judged by the
 * win chance it gave away (Lichess's curve and thresholds), and the reason
 * is given in the evaluation's own terms, by comparing where the best line
 * and the line played lead a few plies on.
 */
object Coach {

    enum class Verdict { BEST, GOOD, INACCURACY, MISTAKE, BLUNDER }

    /** One `analysis` line; `cp` from the side to move's view, mates folded in. */
    data class Analysis(val depth: Int, val cp: Int, val mate: Int?, val best: String, val pv: List<String>)

    data class Review(
        val ply: Int,
        val uci: String,
        val san: String,
        val mover: String,             // "w" or "b"
        val verdict: Verdict,
        val before: Int,               // White's view, best play from the position before
        val after: Int,                // White's view, after the move played
        val loss: Double,              // win chance given away, 0..100
        val best: String,
        val bestSan: String,
        val replySan: String?,
        val bestPv: List<String>,
        val playedPv: List<String>,
        val why: List<Pair<String, Int>>? = null,   // term -> cp, mover's view, worst first
    )

    class GameReview(val plies: List<Review>, val evals: List<Int>)

    fun parse(line: String): Analysis? {
        val p = line.trim().split(Regex("\\s+"))
        if (p.firstOrNull() != "analysis" || p.getOrNull(1) == "none") return null
        fun after(k: String) = p.getOrNull(p.indexOf(k) + 1)
        val kind = after("score")
        val value = p.getOrNull(p.indexOf("score") + 2)?.toIntOrNull() ?: 0
        val mate = if (kind == "mate") value else null
        val cp = when {
            mate == null -> value
            mate > 0 -> 10000 - mate
            else -> -10000 - mate
        }
        val pvAt = p.indexOf("pv")
        return Analysis(after("depth")?.toIntOrNull() ?: 0, cp, mate, after("best") ?: "",
                        if (pvAt >= 0) p.drop(pvAt + 1) else emptyList())
    }

    fun winChance(cp: Int): Double {
        val c = cp.coerceIn(-1000, 1000)
        return 50 + 50 * (2 / (1 + exp(-0.00368208 * c)) - 1)
    }

    fun classify(loss: Double, isBest: Boolean): Verdict = when {
        isBest -> Verdict.BEST
        loss >= 30 -> Verdict.BLUNDER
        loss >= 20 -> Verdict.MISTAKE
        loss >= 10 -> Verdict.INACCURACY
        else -> Verdict.GOOD
    }

    fun glyph(v: Verdict?): String = when (v) {
        Verdict.BLUNDER -> "??"; Verdict.MISTAKE -> "?"; Verdict.INACCURACY -> "?!"; else -> ""
    }

    val Verdict.bad: Boolean get() = this == Verdict.INACCURACY || this == Verdict.MISTAKE || this == Verdict.BLUNDER

    /** Lichess's accuracy, from the mean win chance lost per move. */
    fun accuracy(losses: List<Double>): Double? {
        if (losses.isEmpty()) return null
        return (103.1668 * exp(-0.04354 * losses.average()) - 3.1669).coerceIn(0.0, 100.0)
    }

    fun judge(
        ply: Int, uci: String, san: String, bestSan: String, replySan: String?,
        before: Analysis, after: Analysis?, afterGameEnd: Int?,
    ): Review {
        val mover = if (ply % 2 == 0) "w" else "b"
        val sign = if (mover == "w") 1 else -1
        val isBest = uci == before.best
        val playedCp = if (after != null) -after.cp else afterGameEnd ?: before.cp
        val loss = if (isBest) 0.0 else maxOf(0.0, winChance(before.cp) - winChance(playedCp))
        return Review(ply, uci, san, mover, classify(loss, isBest), sign * before.cp, sign * playedCp, loss,
                      before.best, bestSan, replySan, before.pv, after?.pv ?: emptyList())
    }

    private const val PLIES_AHEAD = 4

    /** The terms that came out worst at the end of the line played, against the best line. */
    suspend fun why(engine: Engine, line: List<String>, r: Review): List<Pair<String, Int>> {
        val a = engine.explainAt(line + r.bestPv.take(PLIES_AHEAD)) ?: return emptyList()
        val b = engine.explainAt(line + r.uci + r.playedPv.take(PLIES_AHEAD - 1)) ?: return emptyList()
        val sign = if (r.mover == "w") 1 else -1
        fun cp(x: Engine.Breakdown, n: String) = x.terms.firstOrNull { it.name == n }?.value ?: 0
        return ((a.terms + b.terms).map { it.name }.toSet() - "rounding")
            .map { it to sign * (cp(b, it) - cp(a, it)) }
            .filter { it.second <= -10 }
            .sortedBy { it.second }
            .take(3)
    }

    /** Every move of a game judged: one analysis per position. */
    suspend fun reviewGame(
        engine: Engine, moves: List<String>, sans: List<String>, movetime: Int,
        onProgress: (Int, Int) -> Unit,
    ): GameReview {
        val total = moves.size + 1
        val found = mutableListOf<Analysis?>()
        val bestSans = mutableListOf<String>()
        for (i in 0 until total) {
            val line = moves.take(i)
            val a = engine.analyse(line, movetime)
            found += a
            bestSans += if (a != null) engine.sanMap(line)[a.best] ?: a.best else ""
            onProgress(i + 1, total)
        }
        // No analysis of the last position means the game ended in it.
        val endForMover: Int? = if (found.last() == null) {
            if (engine.refresh(moves).status["incheck"] == "1") 10000 else 0
        } else null
        val evals = found.mapIndexed { i, a ->
            val sign = if (i % 2 == 0) 1 else -1
            if (a != null) sign * a.cp else -sign * (endForMover ?: 0)
        }
        val plies = mutableListOf<Review>()
        for (i in moves.indices) {
            val before = found[i] ?: break
            val after = found[i + 1]
            plies += judge(i, moves[i], sans[i], bestSans[i],
                           if (after != null) bestSans[i + 1].ifEmpty { after.best } else null,
                           before, after, if (after == null) endForMover else null)
        }
        return GameReview(plies, evals)
    }
}
