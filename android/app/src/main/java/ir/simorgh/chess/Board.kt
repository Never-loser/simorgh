package ir.simorgh.chess

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private const val FILES = "abcdefgh"

/** The desktop app's piece set, generated into res/drawable from its SVG. */
private fun pieceRes(p: Char): Int {
    val side = if (p.isUpperCase()) "w" else "b"
    return when ("${side}_${p.lowercaseChar()}") {
        "w_p" -> R.drawable.piece_w_p; "w_n" -> R.drawable.piece_w_n
        "w_b" -> R.drawable.piece_w_b; "w_r" -> R.drawable.piece_w_r
        "w_q" -> R.drawable.piece_w_q; "w_k" -> R.drawable.piece_w_k
        "b_p" -> R.drawable.piece_b_p; "b_n" -> R.drawable.piece_b_n
        "b_b" -> R.drawable.piece_b_b; "b_r" -> R.drawable.piece_b_r
        "b_q" -> R.drawable.piece_b_q; else -> R.drawable.piece_b_k
    }
}

data class Square(val name: String, val piece: Char?, val file: Int, val rank: Int)

/** Expands a FEN placement field into 64 squares, a8 first. */
fun parsePlacement(fen: String): List<Square> {
    val out = mutableListOf<Square>()
    fen.trim().split(" ").first().split("/").forEachIndexed { row, line ->
        var file = 0
        for (ch in line) {
            if (ch.isDigit()) repeat(ch - '0') { out += Square("${FILES[file]}${8 - row}", null, file, row); file++ }
            else { out += Square("${FILES[file]}${8 - row}", ch, file, row); file++ }
        }
    }
    return out
}

/**
 * The board owns its selection; the screen only learns about finished moves.
 * It is always drawn a1-bottom-left (or flipped, for Black), whatever the
 * interface language: a chessboard is not a text run.
 */
@Composable
fun Board(
    fen: String,
    legal: Set<String>,
    interactive: Boolean,
    flipped: Boolean,
    lastMove: Pair<String, String>?,
    stm: String,
    strings: Strings,
    onMove: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var selected by remember { mutableStateOf<String?>(null) }
    var promotion by remember { mutableStateOf<Pair<String, String>?>(null) }
    if (!interactive && (selected != null || promotion != null)) { selected = null; promotion = null }

    val targets = remember(selected, legal) {
        selected?.let { from -> legal.filter { it.startsWith(from) }.map { it.substring(2, 4) }.toSet() }.orEmpty()
    }

    fun tap(sq: String) {
        if (!interactive) return
        val from = selected
        when {
            from == null -> if (legal.any { it.startsWith(sq) }) selected = sq
            sq == from -> selected = null
            else -> {
                val candidates = legal.filter { it.startsWith(from + sq) }
                when {
                    candidates.size == 1 -> { selected = null; onMove(candidates[0]) }
                    // Several moves share from+to and differ by a suffix: a
                    // promotion. Ask which piece rather than assuming a queen.
                    candidates.size > 1 -> { selected = null; promotion = from to sq }
                    else -> selected = if (legal.any { it.startsWith(sq) }) sq else null
                }
            }
        }
    }

    val squares = parsePlacement(fen).let { if (flipped) it.reversed() else it }

    Box(modifier.fillMaxWidth().aspectRatio(1f)) {
        Column(Modifier.fillMaxSize()) {
            squares.chunked(8).forEach { rank ->
                Row(Modifier.fillMaxWidth().weight(1f)) {
                    rank.forEach { sq ->
                        val light = (sq.file + sq.rank) % 2 == 0
                        val base = when {
                            sq.name == selected -> Ink.Selected
                            lastMove != null && (sq.name == lastMove.first || sq.name == lastMove.second) -> Ink.LastMove
                            light -> Ink.LightSquare
                            else -> Ink.DarkSquare
                        }
                        Box(
                            Modifier.weight(1f).fillMaxSize().background(base).clickable { tap(sq.name) },
                            contentAlignment = Alignment.Center,
                        ) {
                            sq.piece?.let { p ->
                                Image(
                                    painter = painterResource(pieceRes(p)),
                                    contentDescription = null,
                                    modifier = Modifier.fillMaxSize().padding(1.dp),
                                )
                            }
                            if (sq.name in targets) {
                                if (sq.piece == null) {
                                    Box(Modifier.size(13.dp).clip(CircleShape).background(Ink.AccentDim.copy(alpha = 0.85f)))
                                } else {
                                    Box(Modifier.fillMaxSize().padding(3.dp).border(3.dp, Ink.AccentDim.copy(alpha = 0.9f), CircleShape))
                                }
                            }
                            val edgeFile = if (flipped) 7 else 0
                            val edgeRank = if (flipped) 0 else 7
                            if (sq.file == edgeFile) Text(
                                "${sq.name[1]}", fontSize = 8.sp, fontWeight = FontWeight.Medium,
                                color = if (light) Ink.DarkSquare else Ink.LightSquare,
                                modifier = Modifier.align(Alignment.TopStart).padding(2.dp),
                            )
                            if (sq.rank == edgeRank) Text(
                                "${sq.name[0]}", fontSize = 8.sp, fontWeight = FontWeight.Medium,
                                color = if (light) Ink.DarkSquare else Ink.LightSquare,
                                modifier = Modifier.align(Alignment.BottomEnd).padding(2.dp),
                            )
                        }
                    }
                }
            }
        }

        promotion?.let { (from, to) ->
            Box(
                Modifier.fillMaxSize().background(Ink.Bg.copy(alpha = 0.72f))
                    .clickable { promotion = null },
                contentAlignment = Alignment.Center,
            ) {
                Column(
                    Modifier.clip(RoundedCornerShape(12.dp)).background(Ink.Surface)
                        .border(1.dp, Ink.Border, RoundedCornerShape(12.dp)).padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(strings.promote, color = Ink.Fg, fontSize = 14.sp)
                    Row(Modifier.padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        for (suffix in "qrbn") {
                            val glyph = if (stm == "w") suffix.uppercaseChar() else suffix
                            Box(
                                Modifier.size(56.dp).clip(RoundedCornerShape(8.dp)).background(Ink.Surface2)
                                    .clickable { promotion = null; onMove(from + to + suffix) },
                                contentAlignment = Alignment.Center,
                            ) {
                                Image(painterResource(pieceRes(glyph)), null, Modifier.fillMaxSize().padding(4.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}
