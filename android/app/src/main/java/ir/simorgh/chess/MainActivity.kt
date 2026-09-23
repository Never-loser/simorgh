package ir.simorgh.chess

import android.app.Activity
import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { SimorghApp() } }
    }
}

private const val PREFS = "simorgh"

/** The few choices worth remembering between launches. */
private class Prefs(context: Context) {
    private val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    var lang: Lang
        get() = if (p.getString("lang", "fa") == "en") Lang.EN else Lang.FA
        set(v) = p.edit().putString("lang", if (v == Lang.EN) "en" else "fa").apply()
    var elo: Int
        get() = p.getInt("elo", 1600)
        set(v) = p.edit().putInt("elo", v).apply()
    var thinkMs: Int
        get() = p.getInt("thinkMs", 2000)
        set(v) = p.edit().putInt("thinkMs", v).apply()
    var theme: String
        get() = p.getString("theme", "night") ?: "night"
        set(v) = p.edit().putString("theme", v).apply()
}

private val STRENGTHS = listOf(800, 1200, 1600, 2000, 2400, 0)

/** Measured on a Dimensity 1200: the depth each budget actually completes. */
private val THINK_TIMES = listOf(500 to 10, 1000 to 11, 2000 to 13, 3000 to 14, 9000 to 15)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimorghApp() {
    val context = LocalContext.current
    val prefs = remember { Prefs(context) }
    val scope = rememberCoroutineScope()
    val engine = remember { Engine(context) }
    val game = remember { Game(engine, scope) }

    var lang by remember { mutableStateOf(prefs.lang) }
    remember { Ink.use(prefs.theme); 0 }

    // The system bars follow the theme too, or a light theme would sit under
    // a black status bar with white icons.
    val view = LocalView.current
    SideEffect {
        val window = (view.context as? Activity)?.window ?: return@SideEffect
        window.statusBarColor = Ink.Bg.toArgb()
        window.navigationBarColor = Ink.Surface.toArgb()
        WindowCompat.getInsetsController(window, view).apply {
            isAppearanceLightStatusBars = Ink.isLight
            isAppearanceLightNavigationBars = Ink.isLight
        }
    }
    val S = remember(lang) { Strings(lang) }
    var flipped by remember { mutableStateOf(false) }
    var showSettings by remember { mutableStateOf(false) }
    var askColour by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        game.setStrength(prefs.elo)
        game.setThinkTime(prefs.thinkMs)
        game.start()
    }
    // Black at the bottom when playing Black, unless the player flipped it back.
    LaunchedEffect(game.playerColour) { flipped = game.playerColour == "b" }

    val dir = if (lang == Lang.FA) LayoutDirection.Rtl else LayoutDirection.Ltr
    CompositionLocalProvider(LocalLayoutDirection provides dir) {
        Surface(color = Ink.Bg, modifier = Modifier.fillMaxSize()) {
            Column(Modifier.fillMaxSize()) {

                // ---- top bar
                Row(
                    Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(S.appTitle, color = Ink.Accent, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text(S.subtitle, color = Ink.Muted, fontSize = 10.sp, maxLines = 1)
                    }
                    Pill(S.langToggle) { lang = if (lang == Lang.FA) Lang.EN else Lang.FA; prefs.lang = lang }
                    Spacer(Modifier.width(8.dp))
                    Pill(S.settings) { showSettings = true }
                }

                // ---- status
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    val over = game.gameOver
                    Box(Modifier.size(8.dp).clip(CircleShape).background(
                        when { game.error != null -> Ink.Danger; game.thinking -> Ink.Warn; over -> Ink.Muted; else -> Ink.Ok }))
                    Text(statusText(game, S), color = if (over) Ink.Fg else Ink.FgDim, fontSize = 13.sp,
                         fontWeight = if (over) FontWeight.SemiBold else FontWeight.Normal, modifier = Modifier.weight(1f))
                    game.info?.let {
                        Text("${it.depth}", color = Ink.Fg, fontSize = 13.sp)
                        Text(S.depth, color = Ink.Muted, fontSize = 12.sp)
                    }
                }

                // ---- board, always LTR inside whichever layout
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
                    Board(
                        fen = game.state?.fen ?: START_FEN,
                        legal = game.state?.legal.orEmpty(),
                        interactive = game.playersTurn,
                        flipped = flipped,
                        lastMove = game.lastMove,
                        stm = game.stm,
                        strings = S,
                        onMove = game::play,
                    )
                }

                // ---- everything below the board scrolls
                Column(
                    Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState())
                        .padding(horizontal = 12.dp).padding(top = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    EvalBar(game.state?.breakdown?.white)
                    ExplainPanel(game.state?.breakdown, S)
                    MovesPanel(game.moves, S)
                    Spacer(Modifier.height(8.dp))
                }

                // ---- actions
                Row(
                    Modifier.fillMaxWidth().background(Ink.Surface).padding(horizontal = 12.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    ActionButton(S.newGame, Modifier.weight(1.3f), primary = true) { askColour = true }
                    ActionButton(S.undo, Modifier.weight(1f), enabled = !game.thinking && game.moves.isNotEmpty()) { game.undo() }
                    ActionButton(S.flip, Modifier.weight(1f)) { flipped = !flipped }
                }
            }
        }

        // ---- notices
        game.notice?.let { key ->
            LaunchedEffect(key) { delay(2800); game.dismissNotice() }
            Box(Modifier.fillMaxSize().padding(bottom = 76.dp), contentAlignment = Alignment.BottomCenter) {
                Text(
                    if (key == "learned") S.learned else key,
                    color = Ink.Fg, fontSize = 12.5.sp,
                    modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(Ink.Surface2)
                        .border(1.dp, Ink.Border, RoundedCornerShape(20.dp)).padding(horizontal = 14.dp, vertical = 8.dp),
                )
            }
        }

        if (askColour) {
            AlertDialog(
                onDismissRequest = { askColour = false },
                containerColor = Ink.Surface, titleContentColor = Ink.Fg, textContentColor = Ink.FgDim,
                title = { Text(S.newGame) },
                text = { Text(S.playAs) },
                confirmButton = { TextButton(onClick = { askColour = false; game.newGame("w") }) { Text(S.white, color = Ink.Accent) } },
                dismissButton = { TextButton(onClick = { askColour = false; game.newGame("b") }) { Text(S.black, color = Ink.Accent) } },
            )
        }

        if (showSettings) {
            ModalBottomSheet(
                onDismissRequest = { showSettings = false },
                containerColor = Ink.Surface, dragHandle = { BottomSheetDefaults.DragHandle(color = Ink.Border) },
            ) {
                Column(Modifier.padding(horizontal = 18.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(S.settings, color = Ink.Fg, fontSize = 16.sp, fontWeight = FontWeight.Bold)

                    Spacer(Modifier.height(10.dp))
                    Text(S.theme, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        THEMES.forEach { th ->
                            ThemeChip(th, if (lang == Lang.FA) th.nameFa else th.nameEn,
                                      selected = Ink.palette.id == th.id, modifier = Modifier.weight(1f)) {
                                Ink.use(th.id); prefs.theme = th.id
                            }
                        }
                    }

                    Spacer(Modifier.height(10.dp))
                    Text(S.strength, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        STRENGTHS.forEach { elo ->
                            Chip(
                                label = if (elo == 0) S.max else "$elo",
                                sub = null, selected = game.strengthElo == elo, modifier = Modifier.weight(1f),
                            ) { game.setStrength(elo); prefs.elo = elo }
                        }
                    }

                    Spacer(Modifier.height(16.dp))
                    Text(S.thinkTime, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Text(S.thinkHint, color = Ink.Muted, fontSize = 11.sp, lineHeight = 16.sp)
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        THINK_TIMES.forEach { (ms, depth) ->
                            Chip(
                                label = if (ms % 1000 == 0) "${ms / 1000}s" else "${ms / 1000.0}s",
                                sub = "${S.depth} $depth", selected = game.thinkMs == ms, modifier = Modifier.weight(1f),
                            ) { game.setThinkTime(ms); prefs.thinkMs = ms }
                        }
                    }
                }
            }
        }
    }
}

private fun statusText(g: Game, S: Strings): String = when {
    g.error != null -> S.noEngine
    !g.ready -> S.connecting
    g.result == "1-0" -> "${S.checkmate} — ${S.whiteWins}"
    g.result == "0-1" -> "${S.checkmate} — ${S.blackWins}"
    g.fiftyMoves -> S.drawFifty
    g.result == "1/2-1/2" -> S.stalemate
    g.thinking -> S.thinking
    g.inCheck && g.stm == g.playerColour -> "${S.check} — ${S.yourMove}"
    g.stm == g.playerColour -> S.yourMove
    else -> S.engineMove
}

@Composable
private fun EvalBar(white: Int?) {
    val cp = white ?: 0
    val share = (0.5f + (cp.coerceIn(-800, 800) / 1600f)).coerceIn(0.03f, 0.97f)
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Ltr {
            Text(
                white?.let { pawns(it) } ?: "--",
                color = when { white == null -> Ink.Muted; white > 0 -> Ink.Ok; white < 0 -> Ink.Danger; else -> Ink.Fg },
                fontSize = 24.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.width(76.dp),
            )
        }
        Ltr {
            // White against Black, like the pieces themselves: fixed colours
            // in every theme, or a light theme would draw pale on pale.
            Row(Modifier.weight(1f).height(8.dp).clip(RoundedCornerShape(4.dp)).background(Color(0xFF232A33))) {
                Box(Modifier.weight(share).fillMaxHeight().background(Color(0xFFEEF1F4)))
                Box(Modifier.weight(1f - share).fillMaxHeight())
            }
        }
    }
}

@Composable
private fun MovesPanel(moves: List<String>, S: Strings) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Ink.Surface)
            .border(1.dp, Ink.Border, RoundedCornerShape(10.dp)).padding(14.dp),
    ) {
        Text(S.moves, color = Ink.Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        if (moves.isEmpty()) {
            Text(S.noMoves, color = Ink.Muted, fontSize = 12.sp)
            return@Column
        }
        Ltr {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                moves.chunked(2).forEachIndexed { i, pair ->
                    val last = i == moves.lastIndex / 2
                    Row(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(6.dp))
                            .background(if (last) Ink.AccentDim.copy(alpha = 0.35f) else Ink.Surface)
                            .padding(horizontal = 8.dp, vertical = 5.dp),
                    ) {
                        Text("${i + 1}.", color = Ink.Muted, fontSize = 12.5.sp, modifier = Modifier.width(30.dp))
                        Text(pair[0], color = Ink.Fg, fontSize = 13.sp, modifier = Modifier.width(72.dp))
                        Text(pair.getOrNull(1) ?: "", color = Ink.Fg, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun Pill(label: String, onClick: () -> Unit) {
    Text(
        label, color = Ink.FgDim, fontSize = 12.sp,
        modifier = Modifier.clip(RoundedCornerShape(16.dp)).background(Ink.Surface2)
            .border(1.dp, Ink.Border, RoundedCornerShape(16.dp)).clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    )
}

@Composable
private fun ActionButton(label: String, modifier: Modifier, primary: Boolean = false, enabled: Boolean = true, onClick: () -> Unit) {
    Box(
        modifier.height(44.dp).clip(RoundedCornerShape(8.dp))
            .background(if (primary) Ink.Accent else Ink.Surface2)
            .border(1.dp, if (primary) Ink.Accent else Ink.Border, RoundedCornerShape(8.dp))
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = when { !enabled -> Ink.Muted; primary -> Ink.OnAccent; else -> Ink.Fg },
             fontSize = 13.sp, fontWeight = if (primary) FontWeight.SemiBold else FontWeight.Medium)
    }
}

/** A theme, shown as a 2x2 patch of its own board so it can be judged before it is picked. */
@Composable
private fun ThemeChip(th: Palette, name: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(9.dp))
            .background(Ink.Surface2)
            .border(if (selected) 2.dp else 1.dp, if (selected) Ink.Accent else Ink.Border, RoundedCornerShape(9.dp))
            .clickable(onClick = onClick).padding(vertical = 9.dp, horizontal = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Column(Modifier.size(28.dp).clip(RoundedCornerShape(5.dp))) {
            Row(Modifier.weight(1f)) {
                Box(Modifier.weight(1f).fillMaxHeight().background(th.lightSquare))
                Box(Modifier.weight(1f).fillMaxHeight().background(th.darkSquare))
            }
            Row(Modifier.weight(1f)) {
                Box(Modifier.weight(1f).fillMaxHeight().background(th.darkSquare))
                Box(Modifier.weight(1f).fillMaxHeight().background(th.lightSquare))
            }
        }
        Text(name, color = if (selected) Ink.Fg else Ink.FgDim, fontSize = 10.5.sp, maxLines = 1)
    }
}

@Composable
private fun Chip(label: String, sub: String?, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(9.dp))
            .background(if (selected) Ink.AccentDim else Ink.Surface2)
            .border(1.dp, if (selected) Ink.Accent else Ink.Border, RoundedCornerShape(9.dp))
            .clickable(onClick = onClick).padding(vertical = 10.dp, horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Ltr { Text(label, color = if (selected) Ink.OnAccentDim else Ink.FgDim, fontSize = 13.sp, fontWeight = FontWeight.SemiBold) }
        sub?.let { Text(it, color = if (selected) Ink.OnAccentDim.copy(alpha = 0.75f) else Ink.Muted, fontSize = 10.sp) }
    }
}

private const val START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
