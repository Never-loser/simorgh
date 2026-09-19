// Dev-only bridge: pipes the real Simorgh engine over a WebSocket so the
// browser preview (vite) plays against the actual engine. NOT shipped; in the
// packaged app the Rust backend owns the engine directly.
//
//   node dev/engine-bridge.mjs
//
import { spawn } from "node:child_process";
import { WebSocketServer } from "ws";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
// engine + data live in ../../build (built by cmake), run from there so the
// engine's relative data/book.txt and data/weights.txt resolve.
const engineDir = resolve(here, "..", "..", "build");
const engineExe = resolve(engineDir, "simorgh.exe");

if (!existsSync(engineExe)) {
  console.error("engine not found at", engineExe);
  console.error("build it first: cmake --build build");
  process.exit(1);
}

const PORT = 8137;
const wss = new WebSocketServer({ port: PORT });
console.log(`engine bridge on ws://localhost:${PORT} -> ${engineExe}`);

wss.on("connection", (ws) => {
  const proc = spawn(engineExe, { cwd: engineDir });
  let acc = "";
  proc.stdout.on("data", (d) => {
    acc += d.toString();
    const parts = acc.split("\n");
    acc = parts.pop() ?? "";
    for (const line of parts) ws.send(line);
  });
  ws.on("message", (m) => proc.stdin.write(m.toString()));
  ws.on("close", () => proc.kill());
  proc.on("exit", () => ws.close());
});
