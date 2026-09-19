import type { GameState, EngineInfo } from "./types";
import {
  parseFen, parseLegal, parseStatus, parseExplain, parseInfo,
} from "./protocol";

/** A byte channel to one Simorgh process. Two implementations exist:
 *  - Tauri (production): Rust owns the child, we invoke + listen to events.
 *  - WebSocket (dev preview): a tiny Node bridge pipes the real engine, so
 *    the browser preview plays against the actual engine, not a stub. */
export interface Transport {
  start(): Promise<void>;
  send(line: string): void;
  onLine(cb: (line: string) => void): void;
}

class WebSocketTransport implements Transport {
  private ws!: WebSocket;
  private cb: (l: string) => void = () => {};
  private buf: string[] = [];
  constructor(private url = "ws://localhost:8137") {}
  start() {
    return new Promise<void>((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.onmessage = (e) =>
        String(e.data).split("\n").forEach((l) => {
          const line = l.replace(/\r$/, "");
          if (line) this.cb(line);
        });
      this.ws.onopen = () => {
        this.buf.forEach((l) => this.ws.send(l));
        this.buf = [];
        resolve();
      };
      this.ws.onerror = () => reject(new Error("engine bridge not reachable"));
    });
  }
  send(line: string) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(line + "\n");
    else this.buf.push(line + "\n");
  }
  onLine(cb: (l: string) => void) {
    this.cb = cb;
  }
}

class TauriTransport implements Transport {
  private cb: (l: string) => void = () => {};
  private invoke!: (cmd: string, args?: any) => Promise<any>;
  async start() {
    const core = await import("@tauri-apps/api/core");
    const event = await import("@tauri-apps/api/event");
    this.invoke = core.invoke;
    await event.listen<string>("engine-line", (e) => {
      String(e.payload).split("\n").forEach((l) => {
        const line = l.replace(/\r$/, "");
        if (line) this.cb(line);
      });
    });
    await this.invoke("engine_start");
  }
  send(line: string) {
    this.invoke("engine_send", { line });
  }
  onLine(cb: (l: string) => void) {
    this.cb = cb;
  }
}

export function isTauri(): boolean {
  return typeof (window as any).__TAURI_INTERNALS__ !== "undefined";
}

interface Collector {
  lines: string[];
  done: (line: string) => boolean;
  includeDone: boolean;
  onLine?: (line: string) => void;
  resolve: (lines: string[]) => void;
}

export class Engine {
  private t: Transport;
  private collector: Collector | null = null;
  private queue: Promise<any> = Promise.resolve();
  ready = false;

  constructor(transport?: Transport) {
    this.t = transport ?? (isTauri() ? new TauriTransport() : new WebSocketTransport());
    this.t.onLine((l) => this.onLine(l));
  }

  private onLine(line: string) {
    const c = this.collector;
    if (!c) return;
    c.onLine?.(line);
    c.lines.push(line);
    if (c.done(line)) {
      this.collector = null;
      c.resolve(c.includeDone ? c.lines : c.lines.slice(0, -1));
    }
  }

  /** Serialise a command that expects a bounded reply. */
  private run(
    cmd: string | null,
    done: (l: string) => boolean,
    includeDone = true,
    onLine?: (l: string) => void
  ): Promise<string[]> {
    const step = () =>
      new Promise<string[]>((resolve) => {
        this.collector = { lines: [], done, includeDone, onLine, resolve };
        if (cmd !== null) this.t.send(cmd);
      });
    const p = this.queue.then(step);
    this.queue = p.catch(() => {});
    return p;
  }

  async start() {
    await this.t.start();
    await this.run("uci", (l) => l.trim() === "uciok");
    this.ready = true;
  }

  async newGame() {
    this.t.send("ucinewgame");
  }

  async setOption(name: string, value: string | number | boolean) {
    this.t.send(`setoption name ${name} value ${value}`);
  }

  private setPosition(moves: string[]) {
    this.t.send(
      "position startpos" + (moves.length ? " moves " + moves.join(" ") : "")
    );
  }

  /** Full snapshot for a move list: board, legal moves, status, evaluation. */
  async snapshot(moves: string[]): Promise<GameState> {
    this.setPosition(moves);
    const dLines = await this.run("d", (l) => l.startsWith("Key:"));
    const fen = parseFen(dLines);
    const legalLines = await this.run("legal", (l) => l.startsWith("legal"));
    const legal = parseLegal(legalLines[legalLines.length - 1] ?? "");
    const statusLines = await this.run("status", (l) => l.startsWith("status"));
    const status = parseStatus(statusLines[statusLines.length - 1] ?? "");
    const explainLines = await this.run("explain", (l) => l.startsWith("actual"));
    const explain = parseExplain(explainLines);
    return { fen, legal, status, moves: [...moves], explain };
  }

  /** Ask the engine to move. Streams info lines; resolves with bestmove UCI. */
  async go(
    moves: string[],
    movetime: number,
    onInfo?: (info: EngineInfo) => void
  ): Promise<string> {
    this.setPosition(moves);
    const lines = await this.run(
      `go movetime ${movetime}`,
      (l) => l.startsWith("bestmove"),
      true,
      (l) => {
        if (l.startsWith("info ")) onInfo?.(parseInfo(l));
      }
    );
    const last = lines[lines.length - 1] ?? "";
    return last.split(/\s+/)[1] ?? "0000";
  }

  stop() {
    this.t.send("stop");
  }
}
