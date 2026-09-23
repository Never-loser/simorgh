package ir.simorgh.chess

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.roundToInt

// White, draw and black mean the same on every board, like the pieces, so
// the result bars use fixed colours rather than the theme's.
private val WinWhite = Color(0xFFEEF1F4)
private val DrawGrey = Color(0xFF8A939E)
private val WinBlack = Color(0xFF262C34)

/** One line under the board: the ECO code and the name of the game's opening. */
@Composable
fun OpeningLine(opening: Engine.Opening?, atStart: Boolean, S: Strings) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        when {
            atStart -> Text(S.startPos, color = Ink.FgDim, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            opening == null -> Text(S.noOpening, color = Ink.Muted, fontSize = 13.sp)
            else -> {
                Text(
                    opening.eco, color = Ink.Accent, fontSize = 11.5.sp, fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.clip(RoundedCornerShape(5.dp)).background(Ink.Surface2)
                        .border(1.dp, Ink.Border, RoundedCornerShape(5.dp)).padding(horizontal = 6.dp, vertical = 1.dp),
                )
                if (S.lang == Lang.FA)
                    Text(opening.fa, color = Ink.Fg, fontSize = 13.5.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Ltr {
                    Text(
                        opening.name, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        color = if (S.lang == Lang.FA) Ink.Muted else Ink.Fg,
                        fontSize = if (S.lang == Lang.FA) 11.5.sp else 13.5.sp,
                        fontWeight = if (S.lang == Lang.FA) FontWeight.Normal else FontWeight.Bold,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                }
            }
        }
    }
}

/**
 * What the engine's book knows about this position: each move, how often it
 * was played and how those games ended. Tapping a move plays it.
 */
@Composable
fun ExplorerPanel(book: List<Engine.BookMove>, interactive: Boolean, S: Strings, onPlay: (String) -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
            .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
    ) {
        Text(S.explorer, color = Ink.Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(3.dp))
        Text(if (book.isEmpty()) S.noBook else S.explorerHint, color = Ink.Muted, fontSize = 11.sp, lineHeight = 16.sp)
        if (book.isEmpty()) return@Column
        Spacer(Modifier.height(10.dp))

        val total = book.sumOf { it.games }.coerceAtLeast(1)
        // Past the first handful the book's rows are single games: noise.
        book.take(8).forEach { m ->
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(7.dp))
                    .clickable(enabled = interactive) { onPlay(m.uci) }
                    .padding(horizontal = 4.dp, vertical = 7.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Ltr {
                    Text(m.san, color = Ink.Fg, fontSize = 14.sp, fontWeight = FontWeight.Bold,
                         fontFamily = FontFamily.Monospace, modifier = Modifier.width(58.dp))
                }
                Ltr {
                    Row(Modifier.width(76.dp), verticalAlignment = Alignment.Bottom) {
                        Text("%,d".format(m.games), color = Ink.FgDim, fontSize = 12.sp)
                        Text(" ${(m.games * 100.0 / total).roundToInt()}%", color = Ink.Muted, fontSize = 10.5.sp)
                    }
                }
                Ltr { ResultBar(m, Modifier.weight(1f)) }
            }
        }
        Spacer(Modifier.height(6.dp))
        Ltr {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                Text("%,d ${S.games}".format(total), color = Ink.Muted, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun ResultBar(m: Engine.BookMove, modifier: Modifier) {
    val n = m.games.coerceAtLeast(1)
    Row(modifier.height(18.dp).clip(RoundedCornerShape(4.dp))) {
        listOf(Triple(m.white, WinWhite, Color(0xFF1D232B)),
               Triple(m.draws, DrawGrey, Color(0xFF10151B)),
               Triple(m.black, WinBlack, Color(0xFFE6EBF0))).forEach { (count, bg, fg) ->
            if (count > 0) {
                val share = count.toFloat() / n
                Box(Modifier.weight(share).fillMaxHeight().background(bg), contentAlignment = Alignment.Center) {
                    // Only label a segment wide enough to hold the number.
                    if (share >= 0.16f)
                        Text("${(share * 100).roundToInt()}%", color = fg, fontSize = 10.sp,
                             fontWeight = FontWeight.SemiBold, maxLines = 1)
                }
            }
        }
    }
}
