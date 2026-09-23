package ir.simorgh.chess

import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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
import androidx.compose.runtime.CompositionLocalProvider
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs

/**
 * The opening lessons: data/lessons.json, the same file the desktop app
 * teaches from, built and checked by python/lessons.py and copied into the
 * APK's assets by the build.
 */
data class LessonMove(val uci: String, val san: String, val fa: String, val en: String)

data class Lesson(
    val id: String,
    val group: String,
    val side: String,                 // "w" or "b": the side the lesson teaches
    val name: Pair<String, String>,   // fa, en
    val summary: Pair<String, String>,
    val ideas: Pair<List<String>, List<String>>,
    val eco: String,
    val tableName: String,
    val moves: List<LessonMove>,
)

data class LessonGroup(val id: String, val fa: String, val en: String)

class LessonBook(val groups: List<LessonGroup>, val lessons: List<Lesson>) {
    companion object {
        fun load(context: Context): LessonBook {
            val root = JSONObject(context.assets.open("lessons.json").bufferedReader().use { it.readText() })
            fun JSONArray.objects() = (0 until length()).map { getJSONObject(it) }
            fun JSONArray.strings() = (0 until length()).map { getString(it) }
            fun JSONObject.text(k: String) = getJSONObject(k).let { it.getString("fa") to it.getString("en") }
            val groups = root.getJSONArray("groups").objects().map {
                LessonGroup(it.getString("id"), it.getString("fa"), it.getString("en"))
            }
            val lessons = root.getJSONArray("lessons").objects().map { l ->
                Lesson(
                    id = l.getString("id"), group = l.getString("group"), side = l.getString("side"),
                    name = l.text("name"), summary = l.text("summary"),
                    ideas = l.getJSONObject("ideas").let { it.getJSONArray("fa").strings() to it.getJSONArray("en").strings() },
                    eco = l.getString("eco"), tableName = l.getString("tableName"),
                    moves = l.getJSONArray("moves").objects().map {
                        LessonMove(it.getString("uci"), it.getString("san"), it.getString("fa"), it.getString("en"))
                    },
                )
            }
            return LessonBook(groups, lessons)
        }
    }
}

private fun <T> Pair<T, T>.pick(S: Strings): T = if (S.lang == Lang.FA) first else second

private fun signed(cp: Int): String =
    (if (cp > 0) "+" else if (cp < 0) "−" else "±") + String.format("%.2f", abs(cp) / 100.0)

/**
 * The lessons screen: a list of lessons, and a lesson itself, stepped
 * through a move at a time. Each move shows its note and what it changed in
 * the engine's evaluation; the line can be continued as a game at any point.
 */
@Composable
fun LessonsScreen(
    engine: Engine,
    S: Strings,
    onBack: () -> Unit,
    onContinue: (moves: List<String>, sans: List<String>, side: String) -> Unit,
) {
    val context = LocalContext.current
    val book = remember { LessonBook.load(context) }
    var open by remember { mutableStateOf<Lesson?>(null) }

    BackHandler { if (open != null) open = null else onBack() }

    Column(Modifier.fillMaxSize().background(Ink.Bg)) {
        Row(
            Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                if (open == null) S.backToGame else S.allLessons, color = Ink.FgDim, fontSize = 12.sp,
                modifier = Modifier.clip(RoundedCornerShape(16.dp)).background(Ink.Surface2)
                    .border(1.dp, Ink.Border, RoundedCornerShape(16.dp))
                    .clickable { if (open != null) open = null else onBack() }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            )
            Text(open?.name?.pick(S) ?: S.lessons, color = Ink.Fg, fontSize = 17.sp,
                 fontWeight = FontWeight.Bold, maxLines = 1, modifier = Modifier.weight(1f))
        }
        val lesson = open
        if (lesson == null) LessonList(book, S) { open = it }
        else LessonPlayer(lesson, engine, S, onContinue)
    }
}

@Composable
private fun LessonList(book: LessonBook, S: Strings, onPick: (Lesson) -> Unit) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        book.groups.forEach { g ->
            Text(if (S.lang == Lang.FA) g.fa else g.en, color = Ink.Muted, fontSize = 11.5.sp,
                 fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 12.dp, bottom = 2.dp, start = 4.dp, end = 4.dp))
            book.lessons.filter { it.group == g.id }.forEach { l ->
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
                        .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).clickable { onPick(l) }
                        .padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    SideDot(l.side)
                    Column(Modifier.weight(1f)) {
                        Text(l.name.pick(S), color = Ink.Fg, fontSize = 14.5.sp, fontWeight = FontWeight.SemiBold)
                        Text(l.summary.pick(S), color = Ink.Muted, fontSize = 11.5.sp, maxLines = 1,
                             overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                    }
                    Text(l.eco, color = Ink.Accent, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun LessonPlayer(
    lesson: Lesson,
    engine: Engine,
    S: Strings,
    onContinue: (List<String>, List<String>, String) -> Unit,
) {
    var step by remember(lesson.id) { mutableStateOf(0) }
    var flip by remember(lesson.id) { mutableStateOf(false) }
    val snaps = remember(lesson.id) { mutableStateMapOf<Int, Engine.State>() }
    var shown by remember(lesson.id) { mutableStateOf<Engine.State?>(null) }
    val total = lesson.moves.size

    LaunchedEffect(lesson.id, step) {
        for (s in listOf(step, step - 1)) {
            if (s < 0 || snaps.containsKey(s)) continue
            snaps[s] = engine.refresh(lesson.moves.take(s).map { it.uci })
        }
        shown = snaps[step]
    }

    val current = if (step > 0) lesson.moves[step - 1] else null
    val flipped = (lesson.side == "b") != flip

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
        Board(
            fen = shown?.fen ?: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            legal = emptySet(), interactive = false, flipped = flipped,
            lastMove = current?.uci?.let { it.substring(0, 2) to it.substring(2, 4) },
            stm = shown?.status?.get("stm") ?: "w", strings = S, onMove = {},
        )
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            NavButton("⏮", step > 0) { step = 0 }
            NavButton("◀", step > 0) { step -= 1 }
            Text("$step / $total", color = Ink.FgDim, fontSize = 13.sp, modifier = Modifier.width(64.dp),
                 textAlign = androidx.compose.ui.text.style.TextAlign.Center)
            NavButton("▶", step < total, wide = true) { step += 1 }
            NavButton("⏭", step < total) { step = total }
            Spacer(Modifier.weight(1f))
            NavButton("⇅", true) { flip = !flip }
        }
    }

    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        // the line, as a strip of moves to jump between
        Ltr {
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
                    .horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                lesson.moves.forEachIndexed { i, m ->
                    if (i % 2 == 0) Text("${i / 2 + 1}.", color = Ink.Muted, fontSize = 12.sp,
                                         modifier = Modifier.padding(start = 6.dp, end = 2.dp))
                    val cur = step == i + 1
                    Text(
                        m.san, fontFamily = FontFamily.Monospace, fontSize = 13.sp,
                        color = when { cur -> Ink.Fg; step > i -> Ink.FgDim; else -> Ink.Muted },
                        fontWeight = if (cur) FontWeight.Bold else FontWeight.Normal,
                        modifier = Modifier.clip(RoundedCornerShape(5.dp))
                            .background(if (cur) Ink.AccentDim else Color.Transparent)
                            .clickable { step = i + 1 }.padding(horizontal = 5.dp, vertical = 3.dp),
                    )
                }
            }
        }

        // this move
        Card {
            if (current == null) {
                Text(S.lessonStart, color = Ink.FgDim, fontSize = 13.5.sp, lineHeight = 22.sp)
            } else {
                val white = step % 2 == 1
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SideDot(if (white) "w" else "b")
                    Ltr {
                        Text("${(step + 1) / 2}${if (white) "." else "..."} ${current.san}", color = Ink.Fg,
                             fontSize = 17.sp, fontWeight = FontWeight.ExtraBold, fontFamily = FontFamily.Monospace)
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(if (S.lang == Lang.FA) current.fa else current.en, color = Ink.Fg, fontSize = 14.5.sp, lineHeight = 24.sp)
                Delta(snaps[step - 1]?.breakdown, snaps[step]?.breakdown, S)
            }
            Spacer(Modifier.height(12.dp))
            Box(
                Modifier.fillMaxWidth().height(44.dp).clip(RoundedCornerShape(8.dp)).background(Ink.Accent)
                    .clickable {
                        val line = lesson.moves.take(step)
                        onContinue(line.map { it.uci }, line.map { it.san }, lesson.side)
                    },
                contentAlignment = Alignment.Center,
            ) { Text(S.continueVsEngine, color = Ink.OnAccent, fontSize = 13.5.sp, fontWeight = FontWeight.SemiBold) }
        }

        // the lesson
        Card {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(lesson.eco, color = Ink.Accent, fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                Ltr { Text(lesson.tableName, color = Ink.Muted, fontSize = 11.sp, maxLines = 1) }
            }
            Spacer(Modifier.height(8.dp))
            Text(lesson.summary.pick(S), color = Ink.FgDim, fontSize = 13.sp, lineHeight = 21.sp)
            Spacer(Modifier.height(10.dp))
            Text(S.keyIdeas, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            lesson.ideas.pick(S).forEach {
                Row(Modifier.padding(top = 5.dp)) {
                    Text("•", color = Ink.Accent, fontSize = 13.sp, modifier = Modifier.width(14.dp))
                    Text(it, color = Ink.Fg, fontSize = 13.sp, lineHeight = 20.sp)
                }
            }
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                SideDot(lesson.side)
                Text(if (lesson.side == "w") S.lessonAsWhite else S.lessonAsBlack, color = Ink.FgDim, fontSize = 12.sp)
            }
        }
        Spacer(Modifier.height(12.dp))
    }
}

/** What one move changed, term by term, as the engine's evaluation sees it. */
@Composable
private fun Delta(before: Engine.Breakdown?, after: Engine.Breakdown?, S: Strings) {
    if (before == null || after == null) return
    val names = (before.terms + after.terms).map { it.name }.toSet() - "rounding"
    fun cp(b: Engine.Breakdown, n: String) = b.terms.firstOrNull { it.name == n }?.value ?: 0
    val rows = names.map { it to cp(after, it) - cp(before, it) }
        .filter { abs(it.second) >= 5 }.sortedByDescending { abs(it.second) }.take(3)

    Spacer(Modifier.height(10.dp))
    Box(Modifier.fillMaxWidth().height(1.dp).background(Ink.Border))
    Spacer(Modifier.height(8.dp))
    Text(S.engineSees, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    if (rows.isEmpty()) Text(S.noChange, color = Ink.Muted, fontSize = 12.sp, lineHeight = 18.sp, modifier = Modifier.padding(top = 4.dp))
    rows.forEach { (name, d) ->
        Row(Modifier.fillMaxWidth().padding(top = 4.dp)) {
            Text(termName(name, S), color = Ink.FgDim, fontSize = 13.sp, modifier = Modifier.weight(1f))
            Ltr { Text(signed(d), color = if (d > 0) Ink.Fg else Ink.Accent, fontSize = 13.sp, fontWeight = FontWeight.Bold) }
        }
    }
    Row(Modifier.fillMaxWidth().padding(top = 6.dp)) {
        Text(S.evaluation2, color = Ink.Fg, fontSize = 13.sp, modifier = Modifier.weight(1f))
        Ltr { Text("${signed(before.white)} → ${signed(after.white)}", color = Ink.Fg, fontSize = 13.sp, fontWeight = FontWeight.SemiBold) }
    }
    Text(S.deltaLegend, color = Ink.Muted, fontSize = 10.5.sp, modifier = Modifier.padding(top = 4.dp))
}

private fun termName(name: String, S: Strings): String =
    (if (S.lang == Lang.FA) Strings.TERMS_FA else Strings.TERMS_EN)[name] ?: name

@Composable
private fun Card(content: @Composable () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
            .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
    ) { content() }
}

@Composable
private fun SideDot(side: String) {
    Box(Modifier.size(10.dp).clip(CircleShape)
        .background(if (side == "w") Color(0xFFEEF1F4) else Color(0xFF262C34))
        .border(1.dp, Ink.Border, CircleShape))
}

@Composable
private fun NavButton(label: String, enabled: Boolean, wide: Boolean = false, onClick: () -> Unit) {
    Box(
        Modifier.width(if (wide) 64.dp else 42.dp).height(38.dp).clip(RoundedCornerShape(8.dp))
            .background(if (wide) Ink.AccentDim else Ink.Surface2)
            .border(1.dp, if (wide) Ink.Accent else Ink.Border, RoundedCornerShape(8.dp))
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Text(label, color = if (enabled) Ink.Fg else Ink.Muted, fontSize = 14.sp) }
}
