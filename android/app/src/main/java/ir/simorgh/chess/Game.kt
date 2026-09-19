package ir.simorgh.chess

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * One game against the engine. Holds the state the screen renders and the
 * rules of turn-taking; the chess rules themselves stay in the engine, which
 * is asked for the position, the legal moves and the game state after every
 * change so the board and the engine can never disagree.
 */
class Game(private val engine: Engine, private val scope: CoroutineScope) {

    var ready by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    var moves by mutableStateOf(listOf<String>()); private set
    var state by mutableStateOf<Engine.State?>(null); private set
    var info by mutableStateOf<Engine.SearchInfo?>(null); private set
    var thinking by mutableStateOf(false); private set
    var playerColour by mutableStateOf("w"); private set
    var strengthElo by mutableStateOf(1600); private set    // 0 = full strength
    var thinkMs by mutableStateOf(2000); private set         // depth ~13 on a mid phone
    var notice by mutableStateOf<String?>(null)

    private var learned = false
    private var job: Job? = null

    // ---------------------------------------------------------- derived
    val stm: String get() = state?.status?.get("stm") ?: "w"
    val inCheck: Boolean get() = state?.status?.get("incheck") == "1"
    private val legalCount: Int get() = state?.status?.get("legal")?.toIntOrNull() ?: -1
    private val halfmove: Int get() = state?.status?.get("halfmove")?.toIntOrNull() ?: 0

    val gameOver: Boolean get() = state != null && (legalCount == 0 || halfmove >= 100)
    val fiftyMoves: Boolean get() = state != null && legalCount > 0 && halfmove >= 100

    /** "1-0", "0-1", "1/2-1/2", or null while the game is on. */
    val result: String?
        get() = when {
            state == null -> null
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
                applyStrength()
                ready = true
                sync()
                engineTurnIfNeeded()
            } catch (e: Exception) {
                error = e.message ?: e.toString()
            }
        }
    }

    fun newGame(colour: String) {
        if (thinking) return
        scope.launch {
            playerColour = colour
            learned = false
            info = null
            moves = emptyList()
            engine.newGame()
            sync()
            engineTurnIfNeeded()
        }
    }

    /** `move` is a UCI string the engine listed as legal. */
    fun play(move: String) {
        if (!playersTurn) return
        val legal = state?.legal ?: return
        if (move !in legal) return
        scope.launch {
            moves = moves + move
            sync()
            engineTurnIfNeeded()
        }
    }

    /** Back to the last position where it was the player's move. */
    fun undo() {
        if (thinking || moves.isEmpty()) return
        val drop = if (stm == playerColour && moves.size >= 2) 2 else 1
        scope.launch {
            moves = moves.dropLast(drop)
            learned = false
            sync()
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
        thinking = true
        val best = try { engine.go(moves, thinkMs) { info = it } } finally { thinking = false }
        if (best != "0000") {
            moves = moves + best
            sync()
        }
    }

    /** Fold a finished game into the learned book, once. */
    private suspend fun learnIfOver() {
        val r = result ?: return
        if (learned || moves.isEmpty()) return
        learned = true
        engine.learn(moves, r)
        notice = "learned"
    }
}
