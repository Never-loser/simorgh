package ir.simorgh.chess

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.pow
import kotlin.math.roundToInt

/**
 * Puzzles from the Lichess puzzle database (CC0): data/puzzles.tsv, the
 * same file the desktop app uses, chosen by python/puzzles.py. The first
 * move is the opponent's, played for the player; the player finds the
 * rest, and on the last move any mate counts, as on Lichess.
 */
data class Puzzle(val id: String, val fen: String, val moves: List<String>, val rating: Int, val themes: List<String>)

object PuzzleBox {
    fun load(context: Context): List<Puzzle> =
        context.assets.open("puzzles.tsv").bufferedReader().useLines { lines ->
            lines.filter { it.isNotBlank() && !it.startsWith("#") }.map { line ->
                val f = line.split('\t')
                Puzzle(f[0], f[1], f[2].split(' '), f[3].toInt(),
                       f.getOrNull(4)?.split(' ')?.filter { it.isNotBlank() }.orEmpty())
            }.toList()
        }

    private val THEMES = mapOf(
        "mate" to ("مات" to "Mate"), "mateIn1" to ("مات در ۱" to "Mate in 1"),
        "mateIn2" to ("مات در ۲" to "Mate in 2"), "mateIn3" to ("مات در ۳" to "Mate in 3"),
        "fork" to ("چنگال" to "Fork"), "pin" to ("میخ" to "Pin"), "skewer" to ("سیخ" to "Skewer"),
        "hangingPiece" to ("مهره‌ی بی‌دفاع" to "Hanging piece"),
        "discoveredAttack" to ("حمله‌ی بازشونده" to "Discovered attack"),
        "doubleCheck" to ("کیش دوگانه" to "Double check"), "sacrifice" to ("قربانی" to "Sacrifice"),
        "deflection" to ("منحرف کردن" to "Deflection"), "attraction" to ("کشاندن" to "Attraction"),
        "backRankMate" to ("مات ردیف آخر" to "Back-rank mate"), "smotheredMate" to ("مات خفه" to "Smothered mate"),
        "promotion" to ("ارتقا" to "Promotion"), "trappedPiece" to ("مهره‌ی به‌دام‌افتاده" to "Trapped piece"),
        "xRayAttack" to ("حمله‌ی اشعه‌ی ایکس" to "X-ray attack"), "zugzwang" to ("زوگزوانگ" to "Zugzwang"),
        "quietMove" to ("حرکت آرام" to "Quiet move"), "defensiveMove" to ("حرکت دفاعی" to "Defensive move"),
        "kingsideAttack" to ("حمله در جناح شاه" to "Kingside attack"), "interference" to ("مداخله" to "Interference"),
        "clearance" to ("خالی کردن خانه" to "Clearance"), "intermezzo" to ("حرکت میانی" to "Intermezzo"),
        "capturingDefender" to ("گرفتن مدافع" to "Capturing the defender"),
        "exposedKing" to ("شاه بی‌پناه" to "Exposed king"), "advancedPawn" to ("پیاده‌ی پیشرفته" to "Advanced pawn"),
        "endgame" to ("آخربازی" to "Endgame"), "middlegame" to ("وسط‌بازی" to "Middlegame"),
        "opening" to ("گشایش" to "Opening"), "rookEndgame" to ("آخربازی رخ" to "Rook endgame"),
        "pawnEndgame" to ("آخربازی پیاده" to "Pawn endgame"),
    )

    fun theme(id: String, S: Strings): String = THEMES[id]?.let { if (S.lang == Lang.FA) it.first else it.second } ?: id
}

/** The player's puzzle rating and history, kept between launches. */
private class PuzzleRecord(context: Context) {
    private val p = context.getSharedPreferences("simorgh", Context.MODE_PRIVATE)
    var rating: Int
        get() = p.getInt("puzzle.rating", 1200)
        set(v) = p.edit().putInt("puzzle.rating", v).apply()
    var played: Int
        get() = p.getInt("puzzle.played", 0)
        set(v) = p.edit().putInt("puzzle.played", v).apply()
    var streak: Int
        get() = p.getInt("puzzle.streak", 0)
        set(v) = p.edit().putInt("puzzle.streak", v).apply()
    var seen: Set<String>
        get() = p.getStringSet("puzzle.seen", emptySet()) ?: emptySet()
        set(v) = p.edit().putStringSet("puzzle.seen", v).apply()
}

@Composable
fun PuzzleScreen(engine: Engine, S: Strings) {
    val context = LocalContext.current
    val all = remember { PuzzleBox.load(context) }
    val record = remember { PuzzleRecord(context) }
    val scope = rememberCoroutineScope()

    var puzzle by remember { mutableStateOf<Puzzle?>(null) }
    var step by remember { mutableStateOf(0) }
    var state by remember { mutableStateOf<Engine.State?>(null) }
    var busy by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }
    var wrongNow by remember { mutableStateOf(false) }
    var finished by remember { mutableStateOf(false) }
    var delta by remember { mutableStateOf<Int?>(null) }
    var hint by remember { mutableStateOf(emptySet<String>()) }
    var rating by remember { mutableStateOf(record.rating) }
    var round by remember { mutableStateOf(0) }

    fun playerNow() = if (puzzle?.fen?.split(' ')?.getOrNull(1) == "w") "b" else "w"
    fun turnNow() = state != null && !busy && !finished && state?.status?.get("stm") == playerNow()
    val player = playerNow()
    val yourTurn = turnNow()

    fun pickNext(): Puzzle {
        val seen = record.seen
        for (spread in listOf(75, 150, 300, 3000)) {
            val near = all.filter { it.id !in seen && kotlin.math.abs(it.rating - rating) <= spread }
            if (near.isNotEmpty()) return near.random()
        }
        record.seen = emptySet()   // every puzzle done: start the round again
        return all.random()
    }

    suspend fun show() {
        val p = puzzle ?: return
        state = engine.refresh(p.moves.take(step), p.fen)
    }

    /** Score the puzzle once, the first time it is settled. */
    fun settle(solved: Boolean) {
        if (finished) return
        finished = true
        val p = puzzle ?: return
        val expected = 1.0 / (1.0 + 10.0.pow((p.rating - rating) / 400.0))
        val k = if (record.played < 20) 40 else 20   // settle quickly at first
        val change = (k * ((if (solved) 1.0 else 0.0) - expected)).roundToInt()
        rating = maxOf(100, rating + change)
        record.rating = rating
        record.played = record.played + 1
        record.streak = if (solved) record.streak + 1 else 0
        record.seen = record.seen + p.id
        delta = change
    }

    LaunchedEffect(round) {
        puzzle = pickNext()
        step = 0; failed = false; wrongNow = false; finished = false; delta = null; hint = emptySet()
        busy = true
        show()
        delay(600)
        step = 1   // the opponent's move that sets the puzzle
        show()
        busy = false
    }

    // Move handlers must work out whose turn it is when they run, from
    // the state objects. Compose may hand the board a handler remembered
    // from an earlier redraw, whose plain values (like yourTurn) are stale:
    // on a phone that meant every move of the player's was dropped.
    fun onMove(uci: String) {
        val p = puzzle ?: return
        if (!turnNow()) return
        hint = emptySet()
        scope.launch {
            val expected = p.moves[step]
            val after = engine.refresh(p.moves.take(step) + uci, p.fen)
            val mates = after.status["legal"] == "0" && after.status["incheck"] == "1"
            if (uci != expected && !mates) {
                failed = true; wrongNow = true   // not played: the piece goes back
                return@launch
            }
            wrongNow = false
            state = after
            if (uci != expected) { settle(!failed); return@launch }   // a different mate counts
            step += 1
            if (step >= p.moves.size) { settle(!failed); return@launch }
            busy = true
            delay(450)
            step += 1   // the opponent's reply
            show()
            busy = false
            if (step >= p.moves.size) settle(!failed)
        }
    }

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        Board(
            fen = state?.fen ?: puzzle?.fen ?: "8/8/8/8/8/8/8/8 w - - 0 1",
            legal = if (yourTurn) state?.legal.orEmpty() else emptySet(),
            interactive = yourTurn,
            flipped = player == "b",
            lastMove = puzzle?.let { p -> p.moves.getOrNull(step - 1)?.let { it.substring(0, 2) to it.substring(2, 4) } },
            stm = state?.status?.get("stm") ?: player,
            strings = S,
            onMove = { onMove(it) },
            hint = hint,
        )
    }
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.size(12.dp).clip(CircleShape)
                .background(if (player == "w") Color(0xFFEEF1F4) else Color(0xFF262C34)).border(1.dp, Ink.Border, CircleShape))
            Text(if (player == "w") S.pzWhiteToMove else S.pzBlackToMove, color = Ink.Fg, fontSize = 15.sp,
                 fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            Text(S.pzRating, color = Ink.Muted, fontSize = 11.sp)
            Ltr {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("$rating", color = Ink.Fg, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                    delta?.let {
                        Text(if (it > 0) " +$it" else " $it", fontSize = 13.sp, fontWeight = FontWeight.Bold,
                             color = if (it > 0) Ink.Ok else Color(0xFFE0534A))
                    }
                }
            }
        }
        val msg = when {
            finished && !failed -> S.pzSolved
            finished -> S.pzFailed
            wrongNow -> S.pzWrong
            else -> S.pzFind
        }
        Text(msg, color = if (finished && !failed) Ink.Ok else Ink.Fg, fontSize = 13.5.sp, lineHeight = 21.sp,
             fontWeight = if (finished && !failed) FontWeight.Bold else FontWeight.Normal,
             modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Ink.Surface)
                 .border(1.dp, when { finished && !failed -> Ink.Ok; wrongNow -> Color(0xFFE0534A); else -> Ink.Border },
                         RoundedCornerShape(8.dp)).padding(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (!finished) {
                SmallButton(S.egHint, yourTurn) {
                    failed = true
                    puzzle?.moves?.getOrNull(step)?.let { hint = setOf(it.substring(0, 2)) }
                }
                SmallButton(S.pzSolution, !busy) {
                    val p = puzzle ?: return@SmallButton
                    failed = true
                    settle(false)
                    scope.launch {
                        busy = true
                        while (step < p.moves.size) { delay(650); step += 1; show() }
                        busy = false
                    }
                }
            }
            Spacer(Modifier.weight(1f))
            SmallButton(S.pzNext, !busy) { round++ }
        }
        if (finished) {
            puzzle?.let { p ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(S.pzPuzzleRating, color = Ink.FgDim, fontSize = 13.sp, modifier = Modifier.weight(1f))
                    Ltr { Text("${p.rating}", color = Ink.Fg, fontSize = 13.sp, fontWeight = FontWeight.Bold) }
                }
                if (p.themes.isNotEmpty()) Text(p.themes.joinToString(" · ") { PuzzleBox.theme(it, S) },
                                                color = Ink.Accent, fontSize = 12.5.sp)
            }
        }
        Row {
            Text(S.pzPlayed, color = Ink.FgDim, fontSize = 12.5.sp, modifier = Modifier.weight(1f))
            Text("${record.played}", color = Ink.Fg, fontSize = 12.5.sp)
        }
        Row {
            Text(S.pzStreak, color = Ink.FgDim, fontSize = 12.5.sp, modifier = Modifier.weight(1f))
            Text("${record.streak}", color = Ink.Fg, fontSize = 12.5.sp)
        }
        Text(S.pzSource, color = Ink.Muted, fontSize = 11.sp, lineHeight = 17.sp)
        Spacer(Modifier.height(8.dp))
    }
}
