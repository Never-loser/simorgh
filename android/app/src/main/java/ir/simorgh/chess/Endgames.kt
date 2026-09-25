package ir.simorgh.chess

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/**
 * The endgame lessons: data/endgames.json, the same file the desktop app
 * uses, built by python/endgames.py and checked there against the Syzygy
 * tablebase. Each is a position, a goal and the method, played out against
 * the engine at full strength.
 */
data class Endgame(
    val id: String,
    val group: String,
    val goal: String,          // "mate", "promote" or "hold"
    val limit: Int,            // the player's moves
    val fen: String,
    val side: String,
    val name: Pair<String, String>,
    val summary: Pair<String, String>,
    val steps: Pair<List<String>, List<String>>,
)

class EndgameBook(val groups: List<LessonGroup>, val endgames: List<Endgame>) {
    companion object {
        fun load(context: Context): EndgameBook {
            val root = JSONObject(context.assets.open("endgames.json").bufferedReader().use { it.readText() })
            fun JSONArray.objects() = (0 until length()).map { getJSONObject(it) }
            fun JSONArray.strings() = (0 until length()).map { getString(it) }
            fun JSONObject.text(k: String) = getJSONObject(k).let { it.getString("fa") to it.getString("en") }
            return EndgameBook(
                root.getJSONArray("groups").objects().map { LessonGroup(it.getString("id"), it.getString("fa"), it.getString("en")) },
                root.getJSONArray("endgames").objects().map { e ->
                    Endgame(
                        e.getString("id"), e.getString("group"), e.getString("goal"), e.getInt("limit"),
                        e.getString("fen"), e.getString("side"), e.text("name"), e.text("summary"),
                        e.getJSONObject("steps").let { it.getJSONArray("fa").strings() to it.getJSONArray("en").strings() },
                    )
                },
            )
        }
    }
}

private fun <T> Pair<T, T>.pick(S: Strings): T = if (S.lang == Lang.FA) first else second

private class EndgameRecords(context: Context) {
    private val p = context.getSharedPreferences("simorgh", Context.MODE_PRIVATE)
    fun done(id: String) = p.getBoolean("endgame.$id", false)
    fun mark(id: String) = p.edit().putBoolean("endgame.$id", true).apply()
}

@Composable
fun EndgameList(book: EndgameBook, S: Strings, onPick: (Endgame) -> Unit) {
    val records = EndgameRecords(LocalContext.current)
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        book.groups.forEach { g ->
            Text(if (S.lang == Lang.FA) g.fa else g.en, color = Ink.Muted, fontSize = 11.5.sp, fontWeight = FontWeight.Bold,
                 modifier = Modifier.padding(top = 12.dp, bottom = 2.dp, start = 4.dp, end = 4.dp))
            book.endgames.filter { it.group == g.id }.forEach { e ->
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
                        .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).clickable { onPick(e) }
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Box(Modifier.size(10.dp).clip(CircleShape)
                        .background(if (e.side == "w") Color(0xFFEEF1F4) else Color(0xFF262C34)).border(1.dp, Ink.Border, CircleShape))
                    Column(Modifier.weight(1f)) {
                        Text(e.name.pick(S), color = Ink.Fg, fontSize = 14.5.sp, fontWeight = FontWeight.SemiBold)
                        Text(goalText(e, S), color = Ink.Muted, fontSize = 11.5.sp, maxLines = 1)
                    }
                    if (records.done(e.id)) Text("✓", color = Ink.Ok, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

private fun goalText(e: Endgame, S: Strings): String = when (e.goal) {
    "mate" -> S.egGoalMate
    "promote" -> S.egGoalPromote
    else -> S.egGoalHold
}.replace("{n}", "${e.limit}")

@Composable
fun EndgamePlayer(e: Endgame, engine: Engine, S: Strings) {
    val context = LocalContext.current
    val records = remember { EndgameRecords(context) }
    val scope = rememberCoroutineScope()
    var moves by remember(e.id) { mutableStateOf(listOf<String>()) }
    var state by remember(e.id) { mutableStateOf<Engine.State?>(null) }
    var thinking by remember(e.id) { mutableStateOf(false) }
    var hint by remember(e.id) { mutableStateOf(emptySet<String>()) }
    var result by remember(e.id) { mutableStateOf<Pair<Boolean, String>?>(null) }
    var round by remember(e.id) { mutableStateOf(0) }

    val playerMoves = (moves.size + 1) / 2
    val yourTurn = state != null && !thinking && result == null && state?.status?.get("stm") == e.side

    LaunchedEffect(e.id, round) {
        moves = emptyList(); hint = emptySet(); result = null
        engine.newGame()
        state = engine.refresh(emptyList(), e.fen)
    }

    fun pawns(c: String): Int {
        val board = state?.fen?.substringBefore(' ') ?: ""
        return board.count { it == if (c == "w") 'P' else 'p' }
    }

    /** Whether the last move settled the lesson, one way or the other. */
    fun judge(last: String, byPlayer: Boolean) {
        val st = state ?: return
        val noMoves = st.status["legal"] == "0"
        val mated = noMoves && st.status["incheck"] == "1"
        val promoted = last.length == 5
        val other = if (e.side == "w") "b" else "w"
        val played = (moves.size + 1) / 2   // read now, not from the last redraw
        fun finish(won: Boolean, why: String) {
            result = won to why
            if (won) records.mark(e.id)
        }
        if (e.goal == "hold") {
            when {
                mated && byPlayer -> finish(true, S.egWonMate)
                mated -> finish(false, S.egLostMated)
                !byPlayer && promoted -> finish(false, S.egLostPromoted)
                noMoves -> finish(true, S.egWonStalemate)
                pawns(other) == 0 -> finish(true, S.egWonNoPawns)
                byPlayer && played >= e.limit -> finish(true, S.egWonHeld)
            }
            return
        }
        when {
            mated && byPlayer -> finish(true, S.egWonMate)
            mated -> finish(false, S.egLostMated)
            noMoves -> finish(false, S.egLostStalemate)
            e.goal == "promote" && byPlayer && promoted -> finish(true, S.egWonPromoted)
            e.goal == "promote" && pawns(e.side) == 0 -> finish(false, S.egLostPawn)
            (st.status["halfmove"]?.toIntOrNull() ?: 0) >= 100 -> finish(false, S.egLostFifty)
            byPlayer && played >= e.limit -> finish(false, S.egLostLimit)
        }
    }

    fun onMove(uci: String) {
        if (!yourTurn) return
        hint = emptySet()
        scope.launch {
            moves = moves + uci
            state = engine.refresh(moves, e.fen)
            judge(uci, true)
            if (result != null) return@launch
            // The engine plays at full strength: the lesson is only worth
            // anything against best play.
            thinking = true
            try {
                val a = engine.analyse(moves, 800, e.fen) ?: return@launch
                moves = moves + a.best
                state = engine.refresh(moves, e.fen)
                judge(a.best, false)
            } finally {
                thinking = false
            }
        }
    }

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        Board(
            fen = state?.fen ?: e.fen,
            legal = if (yourTurn) state?.legal.orEmpty() else emptySet(),
            interactive = yourTurn,
            flipped = e.side == "b",
            lastMove = moves.lastOrNull()?.let { it.substring(0, 2) to it.substring(2, 4) },
            stm = state?.status?.get("stm") ?: e.side,
            strings = S,
            onMove = ::onMove,
            hint = hint,
        )
    }
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(S.egMoves, color = Ink.FgDim, fontSize = 13.sp)
        Ltr { Text("$playerMoves / ${e.limit}", color = Ink.Fg, fontSize = 13.sp, fontWeight = FontWeight.Bold) }
        Spacer(Modifier.weight(1f))
        SmallButton(S.egHint, yourTurn) {
            scope.launch {
                val a = engine.analyse(moves, 500, e.fen) ?: return@launch
                hint = setOf(a.best.substring(0, 2), a.best.substring(2, 4))
            }
        }
        SmallButton(S.restart, true) { round++ }
    }
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        val r = result
        if (r != null) {
            Column(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp))
                    .background(if (r.first) Ink.Ok.copy(alpha = 0.12f) else Ink.Surface)
                    .border(1.dp, if (r.first) Ink.Ok else Color(0xFFE0534A), RoundedCornerShape(10.dp)).padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(if (r.first) S.egWon else S.egLost, color = Ink.Fg, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                Text(r.second, color = Ink.FgDim, fontSize = 13.sp, lineHeight = 20.sp)
            }
        } else {
            Text(if (thinking) S.thinking else S.egYourMove, color = Ink.FgDim, fontSize = 13.sp)
        }
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
                .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(e.summary.pick(S), color = Ink.FgDim, fontSize = 13.sp, lineHeight = 21.sp)
            Text(goalText(e, S), color = Ink.OnAccentDim, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                 modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Ink.AccentDim).padding(10.dp))
            Text(S.egHow, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            e.steps.pick(S).forEachIndexed { i, step ->
                Row {
                    Text("${i + 1}.", color = Ink.Accent, fontSize = 13.sp, modifier = Modifier.width(20.dp))
                    Text(step, color = Ink.Fg, fontSize = 13.sp, lineHeight = 20.sp)
                }
            }
        }
        Spacer(Modifier.height(12.dp))
    }
}

@Composable
fun SmallButton(label: String, enabled: Boolean, onClick: () -> Unit) {
    Text(label, color = if (enabled) Ink.Fg else Ink.Muted, fontSize = 12.5.sp,
         modifier = Modifier.clip(RoundedCornerShape(8.dp)).background(Ink.Surface2)
             .border(1.dp, Ink.Border, RoundedCornerShape(8.dp)).clickable(enabled = enabled, onClick = onClick)
             .padding(horizontal = 12.dp, vertical = 8.dp))
}
