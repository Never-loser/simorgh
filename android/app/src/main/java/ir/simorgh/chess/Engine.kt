package ir.simorgh.chess

import android.content.Context
import android.os.Build
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
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

    // One engine, two users: the game and the lessons. Each exchange with the
    // engine (a command and the lines it answers with) holds this lock, so a
    // lesson asking for a position cannot interleave with a search.
    private val lock = Mutex()
    private suspend fun <T> exclusive(block: suspend () -> T): T =
        withContext(Dispatchers.IO) { lock.withLock { block() } }
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

    /** The game's opening, as the engine's `opening` command names it. */
    data class Opening(
        val eco: String,         // "B90"
        val name: String,        // "Sicilian Defense: Najdorf Variation"
        val fa: String,          // Persian name of the family
    )

    /** A move the book knows here; results counted for White and Black. */
    data class BookMove(
        val uci: String,
        val san: String,
        val games: Int,
        val white: Int,
        val draws: Int,
        val black: Int,
    )

    data class State(
        val fen: String,
        val legal: Set<String>,
        val san: Map<String, String>,    // UCI -> SAN for every legal move
        val status: Map<String, String>,
        val breakdown: Breakdown?,
        val opening: Opening?,
        val book: List<BookMove>,        // most played first
    )

    data class SearchInfo(val depth: Int, val scoreCp: Int?, val mate: Int?, val nps: Long, val pv: String)

    // ---------------------------------------------------------------- boot

    suspend fun start() = exclusive {
        if (process != null) return@exclusive

        val binary = File(context.applicationInfo.nativeLibraryDir, "libsimorgh.so")
        // What the phone runs decides which jniLibs folder was installed;
        // say so in any failure, it is the first thing a report needs.
        val abis = Build.SUPPORTED_ABIS.joinToString()
        check(binary.exists()) { "no engine for this phone ($abis)" }

        // The engine defaults to data/... relative to its working directory,
        // which means nothing on Android. Copy the data next to it in app
        // storage and hand it absolute paths instead -- both commands already
        // accept them, so this needs no engine change.
        val dataDir = File(context.filesDir, "data").apply { mkdirs() }
        // The book learns from games on the phone, so an existing copy is
        // kept. The weights and the opening names never change here; they
        // are refreshed on every start so an app update brings new ones.
        val book = copyAsset("book.txt", File(dataDir, "book.txt"), refresh = false)
        val weights = copyAsset("weights.txt", File(dataDir, "weights.txt"), refresh = true)
        val openings = copyAsset("openings.tsv", File(dataDir, "openings.tsv"), refresh = true)

        val p = ProcessBuilder(binary.absolutePath)
            .directory(context.filesDir)
            .redirectErrorStream(true)
            .start()
        process = p
        writer = p.outputStream.bufferedWriter()
        reader = p.inputStream.bufferedReader()

        send("uci")
        // A binary that cannot run on this phone starts and dies at once;
        // without this check the app would carry on talking to nothing.
        check(readUntil("uciok").startsWith("uciok")) {
            "engine did not start (${runCatching { p.exitValue() }.getOrNull()?.let { "exit $it" } ?: "no answer"}; $abis)"
        }
        send("weights load ${weights.absolutePath}")
        readUntil("weights")
        send("setoption name Book File value ${book.absolutePath}")
        send("setoption name Openings File value ${openings.absolutePath}")
        send("isready")
        readUntil("readyok")
    }

    private fun copyAsset(name: String, target: File, refresh: Boolean): File {
        // Assets are compressed in the APK, so they are unpacked to files.
        if (!refresh && target.exists() && target.length() > 0) return target
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
    suspend fun refresh(moves: List<String>): State = exclusive {
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

        val breakdown = readExplain()

        send("san")
        val sanParts = readUntil("san").split(" ").filter { it.isNotBlank() }.drop(1)
        val san = sanParts.chunked(2).filter { it.size == 2 }.associate { it[0] to it[1] }

        State(fen, legal, san, status, breakdown, readOpening(), readBook(status["stm"] ?: "w"))
    }

    private fun readOpening(): Opening? {
        send("opening")
        var eco = ""
        var name = ""
        var fa = ""
        while (true) {
            val line = reader?.readLine() ?: return null
            when {
                line == "opening none" -> return null
                line == "opening end" -> return if (eco.isEmpty()) null else Opening(eco, name, fa)
                line.startsWith("opening eco ") -> eco = line.split(" ").getOrNull(2) ?: ""
                line.startsWith("opening name ") -> name = line.removePrefix("opening name ")
                line.startsWith("opening fa ") -> fa = line.removePrefix("opening fa ")
            }
        }
    }

    /**
     * The engine counts wins for the side that played the move; the explorer
     * shows White and Black, so the counts are turned round for Black.
     */
    private fun readBook(stm: String): List<BookMove> {
        send("book")
        val out = mutableListOf<BookMove>()
        while (true) {
            val line = reader?.readLine() ?: break
            if (line == "book end" || line == "book none") break
            val f = line.split(" ").filter { it.isNotBlank() }
            if (f.getOrNull(0) != "book" || f.size < 3) continue
            val w = f.after("w")?.toIntOrNull() ?: 0
            val d = f.after("d")?.toIntOrNull() ?: 0
            val l = f.after("l")?.toIntOrNull() ?: 0
            out += BookMove(
                uci = f[1],
                san = f.after("san") ?: f[1],
                games = f.after("games")?.toIntOrNull() ?: (w + d + l),
                white = if (stm == "w") w else l,
                draws = d,
                black = if (stm == "w") l else w,
            )
        }
        return out.sortedByDescending { it.games }
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

    /**
     * Runs a search, reporting each depth as it completes. `limits` is the
     * rest of the go command: "movetime 2000", or the clock as
     * "wtime .. btime .. winc .. binc ..".
     */
    suspend fun go(
        moves: List<String>,
        limits: String,
        onInfo: (SearchInfo) -> Unit,
    ): String = exclusive {
        position(moves)
        send("go $limits")
        while (true) {
            val line = reader?.readLine() ?: return@exclusive "0000"
            val f = line.split(" ").filter { it.isNotBlank() }
            when (f.getOrNull(0)) {
                "info" -> parseInfo(f)?.let(onInfo)
                "bestmove" -> return@exclusive f.getOrNull(1) ?: "0000"
            }
        }
        @Suppress("UNREACHABLE_CODE") return@exclusive "0000"
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

    /**
     * Ends a search early; its bestmove still arrives, through go(). Not
     * behind the lock on purpose: go() holds it while the search runs.
     */
    fun stopSearch() = send("stop")

    /** UCI -> SAN for every legal move after `moves`; for reading PGN. */
    suspend fun sanMap(moves: List<String>): Map<String, String> = exclusive {
        position(moves)
        send("san")
        readUntil("san").split(" ").filter { it.isNotBlank() }.drop(1)
            .chunked(2).filter { it.size == 2 }.associate { it[0] to it[1] }
    }

    // ------------------------------------------------------------ options

    suspend fun setOption(name: String, value: String) = exclusive {
        send("setoption name $name value $value")
        send("isready")
        readUntil("readyok")
        Unit
    }

    suspend fun newGame() = exclusive {
        send("ucinewgame")
        send("isready")
        readUntil("readyok")
        Unit
    }

    /** Folds a finished game into the learned book, as the desktop GUI does. */
    suspend fun learn(moves: List<String>, result: String) = exclusive {
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
