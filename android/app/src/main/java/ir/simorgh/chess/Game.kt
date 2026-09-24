package ir.simorgh.chess

import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/** Where a game in progress is kept between launches. */
interface GameStore {
    fun save(json: String)
    fun load(): String?
}

/** Base time and increment, in milliseconds; "none" is an untimed game. */
data class TimeControl(val id: String, val baseMs: Long, val incMs: Long) {
    val timed: Boolean get() = baseMs > 0
    val label: String get() = if (timed) id else "∞"
}

val TIME_CONTROLS = listOf(
    TimeControl("none", 0, 0),
    TimeControl("3+2", 180_000, 2_000),
    TimeControl("5+0", 300_000, 0),
    TimeControl("10+0", 600_000, 0),
    TimeControl("15+10", 900_000, 10_000),
)

/**
 * One game against the engine. Holds the state the screen renders and the
 * rules of turn-taking; the chess rules themselves stay in the engine, which
 * is asked for the position, the legal moves and the game state after every
 * change so the board and the engine can never disagree.
 */
class Game(private val engine: Engine, private val scope: CoroutineScope, private val store: GameStore) {

    var ready by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    var moves by mutableStateOf(listOf<String>()); private set
    /** The same moves in SAN, each looked up in the position it was played from. */
    var sanMoves by mutableStateOf(listOf<String>()); private set
    var state by mutableStateOf<Engine.State?>(null); private set
    var info by mutableStateOf<Engine.SearchInfo?>(null); private set
    var thinking by mutableStateOf(false); private set
    var playerColour by mutableStateOf("w"); private set
    var strengthElo by mutableStateOf(1600); private set    // 0 = full strength
    var thinkMs by mutableStateOf(2000); private set         // depth ~13 on a mid phone
    var notice by mutableStateOf<String?>(null)

    // ---------------------------------------------------------- clock
    var timeControl by mutableStateOf(TIME_CONTROLS[0]); private set
    private var remainW by mutableStateOf(0L)   // ms, as of the start of the turn
    private var remainB by mutableStateOf(0L)
    var running by mutableStateOf<String?>(null); private set
    private var turnStart = 0L
    private var paused = false        // the app is in the background
    private var now by mutableStateOf(SystemClock.elapsedRealtime())
    /** The side that ran out of time, if one did. */
    var flagged by mutableStateOf<String?>(null); private set

    fun timeLeft(c: String): Long {
        val r = if (c == "w") remainW else remainB
        return if (running == c) maxOf(0L, r - (now - turnStart)) else r
    }

    private fun setRemain(c: String, ms: Long) { if (c == "w") remainW = ms else remainB = ms }

    private fun clockStart(c: String) {
        if (!timeControl.timed || flagged != null || paused) return
        running = c
        turnStart = SystemClock.elapsedRealtime()
        now = turnStart
    }

    private fun clockStop(c: String, increment: Boolean = true) {
        if (!timeControl.timed || running != c) return
        val used = SystemClock.elapsedRealtime() - turnStart
        setRemain(c, maxOf(0L, (if (c == "w") remainW else remainB) - used) + if (increment) timeControl.incMs else 0)
        running = null
    }

    private fun resetClock() {
        running = null
        flagged = null
        remainW = timeControl.baseMs
        remainB = timeControl.baseMs
    }

    private var learned = false
    private var job: Job? = null

    // ---------------------------------------------------------- derived
    val stm: String get() = state?.status?.get("stm") ?: "w"
    val inCheck: Boolean get() = state?.status?.get("incheck") == "1"
    private val legalCount: Int get() = state?.status?.get("legal")?.toIntOrNull() ?: -1
    private val halfmove: Int get() = state?.status?.get("halfmove")?.toIntOrNull() ?: 0

    val gameOver: Boolean get() = state != null && (legalCount == 0 || halfmove >= 100 || flagged != null)
    val fiftyMoves: Boolean get() = state != null && legalCount > 0 && halfmove >= 100

    /** "1-0", "0-1", "1/2-1/2", or null while the game is on. */
    val result: String?
        get() = when {
            state == null -> null
            flagged != null -> if (flagged == "w") "0-1" else "1-0"
            legalCount == 0 && inCheck -> if (stm == "w") "0-1" else "1-0"
            legalCount == 0 -> "1/2-1/2"
            halfmove >= 100 -> "1/2-1/2"
            else -> null
        }

    val playersTurn: Boolean get() = ready && !thinking && !gameOver && stm == playerColour
    val lastMove: Pair<String, String>?
        get() = moves.lastOrNull()?.let { it.substring(0, 2) to it.substring(2, 4) }

    // ---------------------------------------------------------- lifecycle
    fun start() {
        job = scope.launch {
            try {
                engine.start()
                restore()
                applyStrength()
                ready = true
                sync()
                if (!gameOver) {
                    if (stm == playerColour) clockStart(playerColour) else engineTurnIfNeeded()
                }
            } catch (e: Exception) {
                error = e.message ?: e.toString()
            }
        }
        // The clock's tick: redraws the running clock and notices a flag.
        scope.launch {
            while (true) {
                delay(100)
                val c = running ?: continue
                now = SystemClock.elapsedRealtime()
                if (timeLeft(c) <= 0) {
                    setRemain(c, 0)
                    running = null
                    flagged = c
                    if (thinking) engine.stopSearch()
                    save()
                }
            }
        }
    }

    /**
     * The app went to the background: the clock waits for the player. It
     * stays stopped even if the engine finishes a move meanwhile, and runs
     * again for whoever is to move when the app comes back.
     */
    fun pause() {
        running?.let { clockStop(it, increment = false) }
        paused = true
        save()
    }

    fun resume() {
        paused = false
        if (ready && running == null && !gameOver && timeControl.timed && !thinking) clockStart(stm)
    }

    fun newGame(colour: String) {
        if (thinking) return
        scope.launch {
            playerColour = colour
            learned = false
            info = null
            moves = emptyList()
            sanMoves = emptyList()
            resetClock()
            engine.newGame()
            sync()
            save()
            if (stm == playerColour) clockStart(playerColour)
            engineTurnIfNeeded()
        }
    }

    /** A new game at this time control, same colour. */
    fun playAtTimeControl(tc: TimeControl) {
        if (thinking) return
        timeControl = tc
        newGame(playerColour)
    }

    /** Carry on from a lesson's line as a game, playing the side it teaches. */
    fun startFrom(line: List<String>, sans: List<String>, colour: String) {
        if (thinking) return
        scope.launch {
            playerColour = colour
            learned = false
            info = null
            timeControl = TIME_CONTROLS[0]
            resetClock()
            engine.newGame()
            moves = line
            sanMoves = sans
            sync()
            save()
            engineTurnIfNeeded()
        }
    }

    /** `move` is a UCI string the engine listed as legal. */
    fun play(move: String) {
        if (!playersTurn) return
        val legal = state?.legal ?: return
        if (move !in legal) return
        scope.launch {
            clockStop(playerColour)
            push(move)
            sync()
            save()
            engineTurnIfNeeded()
        }
    }

    /** Back to the last position where it was the player's move. Not against the clock. */
    fun undo() {
        if (thinking || moves.isEmpty() || timeControl.timed) return
        val drop = if (stm == playerColour && moves.size >= 2) 2 else 1
        scope.launch {
            moves = moves.dropLast(drop)
            sanMoves = sanMoves.dropLast(drop)
            learned = false
            sync()
            save()
            // Undoing into the engine's turn (rare: undo right after ours)
            // must not leave the game stalled.
            engineTurnIfNeeded()
        }
    }

    fun setStrength(elo: Int) {
        strengthElo = elo
        scope.launch { applyStrength() }
    }

    fun setThinkTime(ms: Int) { thinkMs = ms }

    fun dismissNotice() { notice = null }

    // ---------------------------------------------------------- PGN
    fun pgn(): String = Pgn.write(Pgn.Info(
        sans = sanMoves,
        // Tag values in plain ASCII: not every program reads anything else.
        white = if (playerColour == "w") "Player" else "Simorgh",
        black = if (playerColour == "b") "Player" else "Simorgh",
        result = result ?: "*",
        eco = state?.opening?.eco,
        opening = state?.opening?.name,
        timeControl = if (timeControl.timed) "${timeControl.baseMs / 1000}+${timeControl.incMs / 1000}" else null,
    ))

    /**
     * Load a game from PGN text and carry on from its last position, playing
     * the side to move. Returns null, or what was wrong: "setup", "empty", or
     * "bad:<n>:<move>" for a move that is not legal where it is played.
     */
    suspend fun importPgn(text: String): String? {
        if (thinking) return "busy"
        val read = Pgn.readMoves(text)
        if (read is Pgn.Read.SetUp) return "setup"
        if (read !is Pgn.Read.Moves) return "empty"
        val line = mutableListOf<String>()
        val sans = mutableListOf<String>()
        read.sans.forEachIndexed { i, written ->
            val want = Pgn.normalize(written)
            val hit = engine.sanMap(line).entries.firstOrNull { Pgn.normalize(it.value) == want }
                ?: return "bad:${i / 2 + 1}${if (i % 2 == 1) "..." else "."}:$written"
            line += hit.key
            sans += hit.value
        }
        playerColour = if (line.size % 2 == 0) "w" else "b"
        learned = true     // someone else's game: not the engine's to learn from
        info = null
        timeControl = TIME_CONTROLS[0]
        resetClock()
        engine.newGame()
        moves = line
        sanMoves = sans
        sync()
        save()
        return null
    }

    // ---------------------------------------------------------- saving
    private fun save() {
        val o = JSONObject()
            .put("moves", JSONArray(moves))
            .put("sans", JSONArray(sanMoves))
            .put("player", playerColour)
            .put("tc", timeControl.id)
            .put("w", timeLeft("w"))
            .put("b", timeLeft("b"))
            .put("flagged", flagged ?: "")
            .put("learned", learned)
        store.save(o.toString())
    }

    private fun restore() {
        val o = runCatching { JSONObject(store.load() ?: return) }.getOrNull() ?: return
        val m = o.optJSONArray("moves") ?: return
        val s = o.optJSONArray("sans") ?: return
        if (m.length() != s.length()) return
        moves = (0 until m.length()).map { m.getString(it) }
        sanMoves = (0 until s.length()).map { s.getString(it) }
        playerColour = o.optString("player", "w")
        timeControl = TIME_CONTROLS.firstOrNull { it.id == o.optString("tc") } ?: TIME_CONTROLS[0]
        remainW = o.optLong("w", timeControl.baseMs)
        remainB = o.optLong("b", timeControl.baseMs)
        flagged = o.optString("flagged").ifEmpty { null }
        learned = o.optBoolean("learned", false)
    }

    // ---------------------------------------------------------- internals
    private suspend fun applyStrength() {
        if (strengthElo == 0) {
            engine.setOption("UCI_LimitStrength", "false")
        } else {
            engine.setOption("UCI_LimitStrength", "true")
            engine.setOption("UCI_Elo", strengthElo.toString())
        }
    }

    private suspend fun sync() {
        state = engine.refresh(moves)
        learnIfOver()
    }

    private suspend fun engineTurnIfNeeded() {
        if (gameOver || stm == playerColour) return
        val side = stm
        clockStart(side)
        thinking = true
        val limits = if (timeControl.timed)
            "wtime ${timeLeft("w")} btime ${timeLeft("b")} winc ${timeControl.incMs} binc ${timeControl.incMs}"
        else "movetime $thinkMs"
        val best = try { engine.go(moves, limits) { info = it } } finally { thinking = false }
        // Out of time while thinking: the move comes too late to count.
        if (best != "0000" && flagged == null) {
            clockStop(side)
            push(best)
            sync()
            if (!gameOver) clockStart(stm)
        }
        save()
    }

    private fun push(move: String) {
        sanMoves = sanMoves + (state?.san?.get(move) ?: move)
        moves = moves + move
    }

    /**
     * Fold a finished game into the learned book, once. Not a game lost on
     * time: the result says nothing about the moves.
     */
    private suspend fun learnIfOver() {
        val r = result ?: return
        if (learned || moves.isEmpty() || flagged != null) return
        learned = true
        engine.learn(moves, r)
        notice = "learned"
    }
}
