package ir.simorgh.chess

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.abs
import kotlin.math.min

/**
 * Numbers inside an RTL screen get their sign moved to the far end: "+0.18"
 * is drawn as "0.18+". A signed value is a left-to-right run whatever
 * language surrounds it, so it is rendered in its own direction.
 */
@Composable
fun Ltr(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr, content = content)
}

fun pawns(cp: Int): String = (if (cp >= 0) "+" else "-") + String.format("%.2f", abs(cp) / 100.0)

/**
 * The panel the app exists for. Every term the engine reports, largest
 * first, each with a bar from a shared centre line; then the total, and a
 * line saying whether that total equals what the engine actually searched
 * on. That check is not decoration: the breakdown is only worth showing if
 * it is exact.
 */
@Composable
fun ExplainPanel(
    breakdown: Engine.Breakdown?,
    strings: Strings,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
            .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
    ) {
        Text(strings.evaluation, color = Ink.Fg, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Text(strings.evalHint, color = Ink.Muted, fontSize = 11.sp, lineHeight = 16.sp,
             modifier = Modifier.padding(top = 3.dp, bottom = 10.dp))

        if (breakdown == null) {
            Text("—", color = Ink.Muted, fontSize = 13.sp)
            return@Column
        }

        val rows = breakdown.terms
            .filter { it.name != "rounding" || it.value != 0 }
            .sortedByDescending { abs(it.value) }

        if (rows.isEmpty()) {
            Text(strings.balanced, color = Ink.Muted, fontSize = 13.sp)
        }
        rows.forEach { t ->
            Row(
                Modifier.fillMaxWidth().padding(vertical = 5.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Column(Modifier.weight(1.15f)) {
                    Text(strings.term(t.name), color = Ink.Fg, fontSize = 13.sp)
                    strings.detail(t.detail).takeIf { it.isNotBlank() }?.let {
                        Text(it, color = Ink.Muted, fontSize = 10.5.sp)
                    }
                }
                DivergingBar(t.value, Modifier.weight(1f))
                Ltr {
                    Text(
                        pawns(t.value),
                        color = when { t.value > 0 -> Ink.Ok; t.value < 0 -> Ink.Danger; else -> Ink.Muted },
                        fontSize = 12.5.sp, fontWeight = FontWeight.SemiBold,
                        textAlign = TextAlign.Start, modifier = Modifier.width(50.dp),
                    )
                }
            }
        }

        Spacer(Modifier.height(6.dp))
        Box(Modifier.fillMaxWidth().height(1.dp).background(Ink.Border))
        Row(
            Modifier.fillMaxWidth().padding(top = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(strings.total, color = Ink.Fg, fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            Text(
                when { breakdown.white > 0 -> strings.favoursWhite; breakdown.white < 0 -> strings.favoursBlack; else -> strings.balanced },
                color = Ink.Muted, fontSize = 11.sp,
            )
            Ltr {
                Text(
                    pawns(breakdown.white),
                    color = when { breakdown.white > 0 -> Ink.Ok; breakdown.white < 0 -> Ink.Danger; else -> Ink.Fg },
                    fontSize = 18.sp, fontWeight = FontWeight.Bold,
                )
            }
        }

        // The engine reports the searched score alongside the breakdown, and
        // Engine.readExplain returns null unless the two agree -- so reaching
        // here with a breakdown means the sum was verified, not assumed.
        Row(Modifier.padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("✓", color = Ink.Ok, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Text(strings.engineScore, color = Ink.Ok, fontSize = 11.5.sp)
            Ltr { Text(pawns(breakdown.white), color = Ink.Ok, fontSize = 11.5.sp) }
            Text("· ${strings.matches}", color = Ink.Ok, fontSize = 11.5.sp)
        }
    }
}

/** A bar from a shared centre: right for White, left for Black, always LTR. */
@Composable
private fun DivergingBar(cp: Int, modifier: Modifier = Modifier) {
    val share = min(0.5f, abs(cp) / 800f)      // 4 pawns fills a half
    Ltr {
        Box(modifier.height(7.dp).clip(RoundedCornerShape(3.5.dp)).background(Ink.Trough)) {
            Row(Modifier.fillMaxWidth().fillMaxHeight()) {
                Box(Modifier.weight(0.5f).fillMaxHeight(), contentAlignment = Alignment.CenterEnd) {
                    if (cp < 0) Box(Modifier.fillMaxHeight().fillMaxWidth(share * 2).background(Ink.Danger.copy(alpha = 0.85f)))
                }
                Box(Modifier.weight(0.5f).fillMaxHeight(), contentAlignment = Alignment.CenterStart) {
                    if (cp > 0) Box(Modifier.fillMaxHeight().fillMaxWidth(share * 2).background(Ink.Ok.copy(alpha = 0.85f)))
                }
            }
            Box(Modifier.align(Alignment.Center).width(1.dp).fillMaxHeight().background(Ink.Muted))
        }
    }
}
