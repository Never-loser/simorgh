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
// The engine is built into cpp/build by `cmake -S cpp -B cpp/build`; an
// older layout put it in build/, which is still accepted. It runs from the
// repository root either way, because that is where its relative
// data/book.txt and data/weights.txt resolve.
const repoRoot = resolve(here, "..", "..");
const engineDir = repoRoot;
const candidates = ["cpp/build/simorgh.exe", "cpp/build/simorgh", "build/simorgh.exe"]
  .map((p) => resolve(repoRoot, p));
const engineExe = candidates.find((p) => existsSync(p));

if (!engineExe) {
  console.error("engine not found; looked at:");
  for (const p of candidates) console.error("  ", p);
  console.error("build it first: cmake -S cpp -B cpp/build && cmake --build cpp/build");
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
