package ir.simorgh.chess

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.Color

/**
 * The colours the whole app draws with, read from the current theme.
 *
 * Every property reads a snapshot state, so a composable that uses, say,
 * Ink.Surface is recomposed when the theme changes -- switching themes
 * repaints the app without any screen having to know themes exist. The
 * palettes themselves are generated from the desktop app (Themes.kt).
 */
object Ink {
    var palette: Palette by mutableStateOf(THEMES.first())

    val isLight: Boolean get() = palette.light

    val Bg: Color get() = palette.bg
    val Trough: Color get() = palette.trough
    val Surface: Color get() = palette.surface
    val Surface2: Color get() = palette.surface2
    val Border: Color get() = palette.border
    val Accent: Color get() = palette.accent
    val AccentDim: Color get() = palette.accentDim
    val OnAccent: Color get() = palette.onAccent
    val OnAccentDim: Color get() = palette.onAccentDim
    val Fg: Color get() = palette.fg
    val FgDim: Color get() = palette.fgDim
    val Muted: Color get() = palette.muted
    val Ok: Color get() = palette.ok
    val Warn: Color get() = palette.warn
    val Danger: Color get() = palette.danger

    val LightSquare: Color get() = palette.lightSquare
    val DarkSquare: Color get() = palette.darkSquare
    val CoordOnLight: Color get() = palette.coordOnLight
    val CoordOnDark: Color get() = palette.coordOnDark
    /** Translucent: drawn over the square colour, so it reads on any board. */
    val Selected: Color get() = palette.selected
    val LastMove: Color get() = palette.lastMove

    fun use(id: String) {
        palette = THEMES.firstOrNull { it.id == id } ?: THEMES.first()
    }
}
