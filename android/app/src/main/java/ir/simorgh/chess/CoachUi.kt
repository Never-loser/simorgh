package ir.simorgh.chess

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.abs
import kotlin.math.roundToInt

// Verdict colours are the usual ones and stay the same in every theme.
private fun Coach.Verdict.color(): Color = when (this) {
    Coach.Verdict.BEST -> Color(0xFF3AA76D)
    Coach.Verdict.GOOD -> Ink.FgDim
    Coach.Verdict.INACCURACY -> Color(0xFFD6B23A)
    Coach.Verdict.MISTAKE -> Color(0xFFE08A36)
    Coach.Verdict.BLUNDER -> Color(0xFFE0534A)
}

fun Coach.Verdict.label(S: Strings): String = when (this) {
    Coach.Verdict.BEST -> S.verdictBest
    Coach.Verdict.GOOD -> S.verdictGood
    Coach.Verdict.INACCURACY -> S.verdictInaccuracy
    Coach.Verdict.MISTAKE -> S.verdictMistake
    Coach.Verdict.BLUNDER -> S.verdictBlunder
}

private fun pawnsOrMate(cp: Int): String = when {
    cp >= 9000 -> "#"
    cp <= -9000 -> "-#"
    else -> (if (cp > 0) "+" else if (cp < 0) "−" else "±") + String.format("%.2f", abs(cp) / 100.0)
}

private fun moveNo(r: Coach.Review) = "${r.ply / 2 + 1}${if (r.mover == "w") "." else "..."}"

/** One line under the board: the verdict on the player's last move. */
@Composable
fun CoachStrip(game: Game, S: Strings) {
    val r = game.lastReview
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 12.dp).padding(bottom = 6.dp)
            .clip(RoundedCornerShape(8.dp)).background(Ink.Surface)
            .border(1.dp, if (game.coaching || r == null) Ink.Border else r.verdict.color(), RoundedCornerShape(8.dp))
            .padding(horizontal = 12.dp, vertical = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (game.coaching || r == null) {
            Text(S.coachThinking, color = Ink.Muted, fontSize = 12.5.sp)
        } else {
            Ltr { Text(r.san + Coach.glyph(r.verdict), color = Ink.Fg, fontWeight = FontWeight.Bold,
                       fontFamily = FontFamily.Monospace, fontSize = 13.sp) }
            Text(r.verdict.label(S), color = r.verdict.color(), fontWeight = FontWeight.Bold, fontSize = 13.sp)
            if (with(Coach) { r.verdict.bad }) {
                Text("· ${S.coachBetter}", color = Ink.FgDim, fontSize = 12.5.sp)
                Ltr { Text(r.bestSan, color = Ink.Fg, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, fontSize = 13.sp) }
            }
        }
    }
}

/** The coach's card for one move. */
@Composable
fun CoachCard(r: Coach.Review?, S: Strings, pending: Boolean = false) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
            .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        Text(S.coachTitle, color = Ink.Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        when {
            pending -> Text(S.coachThinking, color = Ink.Muted, fontSize = 12.5.sp)
            r == null -> Text(S.coachEmpty, color = Ink.Muted, fontSize = 12.5.sp, lineHeight = 19.sp)
            else -> {
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Ink.Surface2)
                        .border(1.dp, r.verdict.color(), RoundedCornerShape(8.dp)).padding(horizontal = 12.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Ltr { Text("${moveNo(r)} ${r.san}", color = Ink.Fg, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold,
                               fontFamily = FontFamily.Monospace) }
                    Spacer(Modifier.weight(1f))
                    Text(r.verdict.label(S), color = r.verdict.color(), fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                InfoRow(S.evaluation2, "${pawnsOrMate(r.before)} → ${pawnsOrMate(r.after)}")
                if (r.verdict == Coach.Verdict.BEST) {
                    Text(S.coachBestNote, color = Ink.FgDim, fontSize = 12.5.sp)
                } else {
                    InfoRow(S.coachLoss, "${r.loss.roundToInt()}%")
                    InfoRow(S.coachBetter, r.bestSan, mono = true)
                    r.replySan?.let { InfoRow(S.coachReply, it, mono = true) }
                    val why = r.why
                    if (!why.isNullOrEmpty()) {
                        Box(Modifier.fillMaxWidth().height(1.dp).background(Ink.Border))
                        Text(S.coachWhy, color = Ink.Muted, fontSize = 11.sp)
                        why.forEach { (name, cp) ->
                            Row(Modifier.fillMaxWidth()) {
                                Text((if (S.lang == Lang.FA) Strings.TERMS_FA else Strings.TERMS_EN)[name] ?: name,
                                     color = Ink.FgDim, fontSize = 13.sp, modifier = Modifier.weight(1f))
                                Ltr { Text(pawnsOrMate(cp), color = Color(0xFFE0534A), fontSize = 13.sp, fontWeight = FontWeight.Bold) }
                            }
                        }
                    } else if (with(Coach) { r.verdict.bad }) {
                        Text(S.coachNoReason, color = Ink.FgDim, fontSize = 12.sp, lineHeight = 18.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String, mono: Boolean = false) {
    Row(Modifier.fillMaxWidth()) {
        Text(label, color = Ink.FgDim, fontSize = 13.sp, modifier = Modifier.weight(1f))
        Ltr { Text(value, color = Ink.Fg, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                   fontFamily = if (mono) FontFamily.Monospace else FontFamily.Default) }
    }
}

/** Progress of a running review, or the arrows of an open one. */
@Composable
fun ReviewBar(game: Game, S: Strings) {
    val p = game.reviewProgress
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 12.dp).padding(bottom = 6.dp)
            .clip(RoundedCornerShape(8.dp)).background(Ink.Surface).border(1.dp, Ink.Accent, RoundedCornerShape(8.dp))
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (p != null) {
            Text(S.reviewRunning, color = Ink.FgDim, fontSize = 12.5.sp)
            Box(Modifier.weight(1f).height(6.dp).clip(RoundedCornerShape(3.dp)).background(Ink.Surface2)) {
                Box(Modifier.fillMaxWidth(p.first.toFloat() / p.second).height(6.dp).background(Ink.Accent))
            }
            Ltr { Text("${p.first}/${p.second}", color = Ink.Muted, fontSize = 12.sp) }
        } else {
            val n = game.gameReview?.plies?.size ?: 0
            Ltr {
                Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    NavChip("◀", game.reviewSel > 0) { game.selectReview(game.reviewSel - 1) }
                    val sel = game.reviewSel
                    Text(if (sel >= 0) "${sel / 2 + 1}${if (sel % 2 == 1) "..." else "."} ${game.sanMoves.getOrNull(sel) ?: ""}" else "",
                         color = Ink.Fg, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold, fontSize = 14.sp,
                         modifier = Modifier.weight(1f))
                    NavChip("▶", game.reviewSel < n - 1) { game.selectReview(game.reviewSel + 1) }
                }
            }
            NavChip(S.reviewClose, true) { game.closeReview() }
        }
    }
}

@Composable
private fun NavChip(label: String, enabled: Boolean, onClick: () -> Unit) {
    Text(label, color = if (enabled) Ink.Fg else Ink.Muted, fontSize = 13.sp,
         modifier = Modifier.clip(RoundedCornerShape(7.dp)).background(Ink.Surface2)
             .border(1.dp, Ink.Border, RoundedCornerShape(7.dp)).clickable(enabled = enabled, onClick = onClick)
             .padding(horizontal = 12.dp, vertical = 6.dp))
}

/** The review itself: accuracy and counts, the graph, the moves, the card. */
@Composable
fun ReviewPanel(game: Game, S: Strings) {
    val review = game.gameReview ?: return
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
                .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(S.reviewTitle, color = Ink.Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            val sides = listOf("w", "b").map { c -> review.plies.filter { it.mover == c } }
            SummaryRow("", S.white, S.black, header = true)
            SummaryRow(S.accuracy, *sides.map { s -> Coach.accuracy(s.map { it.loss })?.let { "${it.roundToInt()}%" } ?: "—" }.toTypedArray(), bold = true)
            Coach.Verdict.values().forEach { v ->
                SummaryRow(v.label(S), *sides.map { s -> "${s.count { it.verdict == v }}" }.toTypedArray(),
                           color = if (v == Coach.Verdict.GOOD) Ink.Fg else v.color())
            }
            Spacer(Modifier.height(4.dp))
            Graph(review, game.reviewSel) { game.selectReview(it) }
            Spacer(Modifier.height(4.dp))
            // The moves, a few pairs a row, coloured by verdict.
            Ltr {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    review.plies.chunked(8).forEach { row ->
                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            row.forEach { p ->
                                if (p.mover == "w") Text("${p.ply / 2 + 1}.", color = Ink.Muted, fontSize = 11.5.sp,
                                                         modifier = Modifier.padding(top = 3.dp))
                                Text(p.san + Coach.glyph(p.verdict), fontFamily = FontFamily.Monospace, fontSize = 12.5.sp,
                                     color = if (p.verdict == Coach.Verdict.GOOD || p.verdict == Coach.Verdict.BEST) Ink.FgDim else p.verdict.color(),
                                     fontWeight = if (p.verdict == Coach.Verdict.BLUNDER) FontWeight.Bold else FontWeight.Normal,
                                     modifier = Modifier.clip(RoundedCornerShape(4.dp))
                                         .background(if (p.ply == game.reviewSel) Ink.AccentDim else Color.Transparent)
                                         .clickable { game.selectReview(p.ply) }.padding(horizontal = 3.dp, vertical = 2.dp))
                            }
                        }
                    }
                }
            }
        }
        CoachCard(review.plies.getOrNull(game.reviewSel), S)
    }
}

@Composable
private fun SummaryRow(label: String, vararg values: String, header: Boolean = false, bold: Boolean = false, color: Color = Ink.Fg) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = Ink.FgDim, fontSize = 12.5.sp, modifier = Modifier.weight(1.4f))
        values.forEachIndexed { i, v ->
            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                if (header) {
                    Box(Modifier.size(9.dp).clip(CircleShape).background(if (i == 0) Color(0xFFEEF1F4) else Color(0xFF262C34))
                        .border(1.dp, Ink.Border, CircleShape))
                    Spacer(Modifier.width(5.dp))
                }
                Ltr { Text(v, color = if (header) Ink.FgDim else color, fontSize = if (bold) 15.sp else 12.5.sp,
                           fontWeight = if (bold || header) FontWeight.Bold else FontWeight.Normal) }
            }
        }
    }
}

/** White's win chance through the game; tap to pick a move. Fixed colours, like the eval bar. */
@Composable
private fun Graph(review: Coach.GameReview, selected: Int, onPick: (Int) -> Unit) {
    val n = maxOf(1, review.evals.size - 1)
    Ltr {
        Canvas(
            Modifier.fillMaxWidth().height(110.dp).clip(RoundedCornerShape(8.dp))
                .pointerInput(review) {
                    detectTapGestures { pos ->
                        val i = (pos.x / size.width * n).roundToInt()
                        onPick((i - 1).coerceIn(0, review.plies.size - 1))
                    }
                },
        ) {
            val w = size.width
            val h = size.height
            fun x(i: Int) = i.toFloat() / n * w
            fun y(cp: Int) = h - (Coach.winChance(cp) / 100f).toFloat() * h
            drawRect(Color(0xFF262C34))
            val path = Path().apply {
                moveTo(0f, h)
                review.evals.forEachIndexed { i, e -> lineTo(x(i), y(e)) }
                lineTo(w, h)
                close()
            }
            drawPath(path, Color(0xFFDFE4EA))
            drawLine(Color(0xFF8A939E), Offset(0f, h / 2), Offset(w, h / 2), strokeWidth = 1.5f,
                     pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 8f)))
            if (selected >= 0) drawLine(Ink.Accent, Offset(x(selected + 1), 0f), Offset(x(selected + 1), h), strokeWidth = 4f)
            review.plies.filter { with(Coach) { it.verdict.bad } }.forEach { p ->
                val c = Offset(x(p.ply + 1), y(review.evals[p.ply + 1]))
                drawCircle(Color(0xFF10151B), 9f, c)
                drawCircle(p.verdict.color(), 7f, c)
            }
        }
    }
}
