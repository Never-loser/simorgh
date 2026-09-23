package ir.simorgh.chess

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import kotlin.math.floor
import kotlin.math.roundToInt

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
 * The board owns selection and dragging; the screen only hears about
 * finished moves. A move can be made either way: tap the piece then the
 * square, or drag it there. Both stay available because on a phone a finger
 * covers the piece it is dragging, and some players would rather tap.
 *
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
    var dragFrom by remember { mutableStateOf<String?>(null) }
    var dragAt by remember { mutableStateOf(Offset.Zero) }
    if (!interactive && (selected != null || promotion != null || dragFrom != null)) {
        selected = null; promotion = null; dragFrom = null
    }

    val squares = remember(fen) { parsePlacement(fen) }
    val pieceOn = remember(squares) { squares.associate { it.name to it.piece } }
    val origin = dragFrom ?: selected
    val targets = remember(origin, legal) {
        origin?.let { from -> legal.filter { it.startsWith(from) }.map { it.substring(2, 4) }.toSet() }.orEmpty()
    }

    // Gesture handlers are installed once and outlive recompositions, so they
    // read the latest game state through these rather than capturing it.
    val legalNow by rememberUpdatedState(legal)
    val interactiveNow by rememberUpdatedState(interactive)
    val onMoveNow by rememberUpdatedState(onMove)
    val pieceOnNow by rememberUpdatedState(pieceOn)
    val haptics = LocalHapticFeedback.current

    /** Plays from->to if it is legal; asks which piece if it is a promotion. */
    fun attempt(from: String, to: String): Boolean {
        val candidates = legalNow.filter { it.startsWith(from + to) }
        return when {
            candidates.size == 1 -> { selected = null; onMoveNow(candidates[0]); true }
            // Several legal moves share from+to and differ by a suffix: a
            // promotion. Ask rather than assuming a queen.
            candidates.size > 1 -> { selected = null; promotion = from to to; true }
            else -> false
        }
    }

    fun movable(sq: String) = legalNow.any { it.startsWith(sq) }

    fun tap(sq: String) {
        if (!interactiveNow || promotion != null) return
        val from = selected
        when {
            from == null -> if (movable(sq)) selected = sq
            sq == from -> selected = null
            !attempt(from, sq) -> selected = if (movable(sq)) sq else null
        }
    }

    BoxWithConstraints(modifier.fillMaxWidth().aspectRatio(1f)) {
        val cellPx = with(LocalDensity.current) { maxWidth.toPx() } / 8f

        fun squareAt(p: Offset): String? {
            val col = floor(p.x / cellPx).toInt()
            val row = floor(p.y / cellPx).toInt()
            if (col !in 0..7 || row !in 0..7) return null
            return if (flipped) "${FILES[7 - col]}${row + 1}" else "${FILES[col]}${8 - row}"
        }

        val hover = dragFrom?.let { squareAt(dragAt) }

        Box(
            Modifier.fillMaxSize()
                .pointerInput(flipped, cellPx) {
                    detectTapGestures(onTap = { p -> squareAt(p)?.let(::tap) })
                }
                .pointerInput(flipped, cellPx) {
                    detectDragGestures(
                        onDragStart = { p ->
                            val sq = squareAt(p)
                            if (interactiveNow && promotion == null && sq != null &&
                                pieceOnNow[sq] != null && movable(sq)
                            ) {
                                dragFrom = sq
                                selected = sq
                                dragAt = p
                                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                            }
                        },
                        onDrag = { change, amount ->
                            if (dragFrom != null) { change.consume(); dragAt += amount }
                        },
                        onDragEnd = {
                            val from = dragFrom
                            val to = squareAt(dragAt)
                            dragFrom = null
                            // A drop that is not a legal move leaves the piece
                            // selected, so its targets stay on screen and a tap
                            // can still finish the move.
                            if (from != null && (to == null || to == from || !attempt(from, to))) {
                                selected = from
                            }
                        },
                        onDragCancel = { dragFrom = null },
                    )
                },
        ) {
            // ---- squares and their markings
            Column(Modifier.fillMaxSize()) {
                (if (flipped) squares.reversed() else squares).chunked(8).forEach { rank ->
                    Row(Modifier.fillMaxWidth().weight(1f)) {
                        rank.forEach { sq ->
                            val light = (sq.file + sq.rank) % 2 == 0
                            Box(
                                Modifier.weight(1f).fillMaxSize()
                                    .background(if (light) Ink.LightSquare else Ink.DarkSquare),
                                contentAlignment = Alignment.Center,
                            ) {
                                if (lastMove != null && (sq.name == lastMove.first || sq.name == lastMove.second))
                                    Box(Modifier.fillMaxSize().background(Ink.LastMove))
                                if (sq.name == origin)
                                    Box(Modifier.fillMaxSize().background(Ink.Selected))
                                if (sq.name == hover && sq.name != dragFrom)
                                    Box(Modifier.fillMaxSize().border(3.dp, Ink.Accent))

                                sq.piece?.let { p ->
                                    Image(
                                        painter = painterResource(pieceRes(p)),
                                        contentDescription = null,
                                        // The piece being dragged leaves a ghost
                                        // behind so its origin stays readable.
                                        modifier = Modifier.fillMaxSize().padding(1.dp)
                                            .alpha(if (sq.name == dragFrom) 0.28f else 1f),
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
                                val coord = if (light) Ink.CoordOnLight else Ink.CoordOnDark
                                if (sq.file == edgeFile) Text(
                                    "${sq.name[1]}", fontSize = 8.sp, fontWeight = FontWeight.Medium, color = coord,
                                    modifier = Modifier.align(Alignment.TopStart).padding(2.dp),
                                )
                                if (sq.rank == edgeRank) Text(
                                    "${sq.name[0]}", fontSize = 8.sp, fontWeight = FontWeight.Medium, color = coord,
                                    modifier = Modifier.align(Alignment.BottomEnd).padding(2.dp),
                                )
                            }
                        }
                    }
                }
            }

            // ---- the piece in hand, drawn above the board. It is lifted a
            // little above the fingertip and enlarged, so the finger doing the
            // dragging does not hide what it is carrying.
            dragFrom?.let { from ->
                pieceOn[from]?.let { p ->
                    val size = with(LocalDensity.current) { cellPx.toDp() }
                    Image(
                        painter = painterResource(pieceRes(p)),
                        contentDescription = null,
                        modifier = Modifier
                            .zIndex(2f)
                            .offset {
                                IntOffset(
                                    (dragAt.x - cellPx / 2).roundToInt(),
                                    (dragAt.y - cellPx * 0.9f).roundToInt(),
                                )
                            }
                            .size(size)
                            .scale(1.25f),
                    )
                }
            }
        }

        // ---- promotion choice
        promotion?.let { (from, to) ->
            Box(
                Modifier.fillMaxSize().background(Ink.Bg.copy(alpha = 0.72f)).clickable { promotion = null },
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
