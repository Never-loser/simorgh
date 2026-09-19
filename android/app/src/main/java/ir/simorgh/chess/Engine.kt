package ir.simorgh.chess

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.BufferedWriter
import java.io.File

/**
 * Talks to the Simorgh binary over its stdin/stdout, exactly as the desktop
 * front end does.
 *
 * The engine ships as `libsimorgh.so` in jniLibs rather than as a shared
 * library loaded through JNI. It is an ordinary executable, and naming it
 * that way is what makes Android extract it at install time with the
 * execute bit set. Nothing in the engine changes for Android as a result --
 * the same UCI conversation works here as on a desktop.
 *
 * Like the desktop front end, this class implements no chess rules of its
 * own. It asks the engine for the position, the legal moves and the game
 * state, so the board on screen and the engine's idea of the game cannot
 * drift apart.
 */
class Engine(private val context: Context) {

    private var process: Process? = null
    private var writer: BufferedWriter? = null
    private var reader: BufferedReader? = null

    data class Term(
        val name: String,
        val value: Int,          // centipawns, from White's point of view
        val detail: String,
    )

    data class Breakdown(
        val terms: List<Term>,
        val white: Int,          // total from White's point of view
        val phase: Int,
        val phaseMax: Int,
    )

    data class State(
        val fen: String,
        val legal: Set<String>,
        val status: Map<String, String>,
        val breakdown: Breakdown?,
    )

    data class SearchInfo(val depth: Int, val scoreCp: Int?, val mate: Int?, val nps: Long, val pv: String)

    // ---------------------------------------------------------------- boot

    suspend fun start() = withContext(Dispatchers.IO) {
        if (process != null) return@withContext

        val binary = File(context.applicationInfo.nativeLibraryDir, "libsimorgh.so")
        check(binary.exists()) { "engine missing at ${binary.absolutePath}" }

        // The engine defaults to data/... relative to its working directory,
        // which means nothing on Android. Copy the data next to it in app
        // storage and hand it absolute paths instead -- both commands already
        // accept them, so this needs no engine change.
        val dataDir = File(context.filesDir, "data").apply { mkdirs() }
        val book = copyAsset("book.txt", File(dataDir, "book.txt"))
        val weights = copyAsset("weights.txt", File(dataDir, "weights.txt"))

        val p = ProcessBuilder(binary.absolutePath)
            .directory(context.filesDir)
            .redirectErrorStream(true)
            .start()
        process = p
        writer = p.outputStream.bufferedWriter()
        reader = p.inputStream.bufferedReader()

        send("uci")
        readUntil("uciok")
        send("weights load ${weights.absolutePath}")
        readUntil("weights")
        send("setoption name Book File value ${book.absolutePath}")
        send("isready")
        readUntil("readyok")
    }

    private fun copyAsset(name: String, target: File): File {
        // Assets are compressed in the APK, so this unpacks once per install.
        if (target.exists() && target.length() > 0) return target
        context.assets.open(name).use { input ->
            target.outputStream().use { output -> input.copyTo(output) }
        }
        return target
    }

    // ------------------------------------------------------------ plumbing

    private fun send(command: String) {
        val w = writer ?: return
        w.write(command)
        w.write("\n")
        w.flush()
    }

    private fun readUntil(prefix: String): String {
        val r = reader ?: return ""
        while (true) {
            val line = r.readLine() ?: return ""
            if (line.startsWith(prefix)) return line
        }
    }

    private fun position(moves: List<String>) {
        send(if (moves.isEmpty()) "position startpos"
             else "position startpos moves " + moves.joinToString(" "))
    }

    // -------------------------------------------------------------- state

    /**
     * Everything the board needs for one position, in a single round trip.
     * The breakdown rides along so the explanation and the board can never
     * be showing different positions.
     */
    suspend fun refresh(moves: List<String>): State = withContext(Dispatchers.IO) {
        position(moves)

        send("d")
        var fen = ""
        while (true) {
            val line = reader?.readLine() ?: break
            if (line.startsWith("Fen:")) fen = line.removePrefix("Fen:").trim()
            if (line.startsWith("Key:")) break
        }

        send("legal")
        val legal = readUntil("legal").split(" ").drop(1).filter { it.isNotBlank() }.toSet()

        send("status")
        val parts = readUntil("status").split(" ")
        val status = buildMap {
            var i = 1
            while (i + 1 < parts.size) { put(parts[i], parts[i + 1]); i += 2 }
        }

        State(fen, legal, status, readExplain())
    }

    private fun readExplain(): Breakdown? {
        send("explain")
        val terms = mutableListOf<Term>()
        var white: Int? = null
        var score: Int? = null
        var phase = 0
        var phaseMax = 1
        while (true) {
            val line = reader?.readLine() ?: return null
            val f = line.split(" ").filter { it.isNotBlank() }
            when {
                f.getOrNull(0) == "explain" -> f.getOrNull(2)?.split("/")?.let {
                    phase = it[0].toIntOrNull() ?: 0
                    phaseMax = it.getOrNull(1)?.toIntOrNull() ?: 1
                }
                f.getOrNull(0) == "term" -> {
                    val on = f.indexOf("on")
                    terms += Term(
                        name = f[1],
                        value = f[2].toIntOrNull() ?: 0,
                        detail = if (on > 0) f.drop(on + 1).joinToString(" ") else "",
                    )
                }
                f.getOrNull(0) == "white" -> white = f[1].toIntOrNull()
                f.getOrNull(0) == "score" -> score = f[1].toIntOrNull()
                f.getOrNull(0) == "actual" -> {
                    // The engine prints both so the sum can be checked here
                    // rather than trusted. A mismatch means the breakdown has
                    // fallen behind the evaluation; report nothing rather than
                    // a confident wrong answer.
                    val actual = f[1].toIntOrNull()
                    if (white == null || score == null || score != actual) return null
                    if (terms.sumOf { it.value } != white) return null
                    return Breakdown(terms, white, phase, phaseMax)
                }
            }
        }
    }

    // ------------------------------------------------------------- search

    /** Runs a search, reporting each depth as it completes. */
    suspend fun go(
        moves: List<String>,
        movetimeMs: Int,
        onInfo: (SearchInfo) -> Unit,
    ): String = withContext(Dispatchers.IO) {
        position(moves)
        send("go movetime $movetimeMs")
        while (true) {
            val line = reader?.readLine() ?: return@withContext "0000"
            val f = line.split(" ").filter { it.isNotBlank() }
            when (f.getOrNull(0)) {
                "info" -> parseInfo(f)?.let(onInfo)
                "bestmove" -> return@withContext f.getOrNull(1) ?: "0000"
            }
        }
        @Suppress("UNREACHABLE_CODE") return@withContext "0000"
    }

    private fun parseInfo(f: List<String>): SearchInfo? {
        val depth = f.after("depth")?.toIntOrNull() ?: return null
        val scoreAt = f.indexOf("score")
        var cp: Int? = null
        var mate: Int? = null
        if (scoreAt >= 0) {
            val kind = f.getOrNull(scoreAt + 1)
            val value = f.getOrNull(scoreAt + 2)?.toIntOrNull()
            if (kind == "cp") cp = value else if (kind == "mate") mate = value
        }
        val pvAt = f.indexOf("pv")
        return SearchInfo(
            depth = depth,
            scoreCp = cp,
            mate = mate,
            nps = f.after("nps")?.toLongOrNull() ?: 0L,
            pv = if (pvAt >= 0) f.drop(pvAt + 1).joinToString(" ") else "",
        )
    }

    private fun List<String>.after(key: String): String? {
        val i = indexOf(key)
        return if (i >= 0) getOrNull(i + 1) else null
    }

    // ------------------------------------------------------------ options

    suspend fun setOption(name: String, value: String) = withContext(Dispatchers.IO) {
        send("setoption name $name value $value")
        send("isready")
        readUntil("readyok")
        Unit
    }

    suspend fun newGame() = withContext(Dispatchers.IO) {
        send("ucinewgame")
        send("isready")
        readUntil("readyok")
        Unit
    }

    /** Folds a finished game into the learned book, as the desktop GUI does. */
    suspend fun learn(moves: List<String>, result: String) = withContext(Dispatchers.IO) {
        position(moves)
        send("learn $result")
        readUntil("info string")
        Unit
    }

    fun stop(scope: CoroutineScope) {
        scope.launch(Dispatchers.IO) {
            runCatching { send("quit"); process?.waitFor() }
                .onFailure { process?.destroy() }
            process = null
        }
    }
}
