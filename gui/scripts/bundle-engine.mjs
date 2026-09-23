// Build the C++ engine and copy it, with its data, into the Tauri resources
// so `npm run tauri build` can bundle a self-contained app. Run before the
// first build (and whenever the engine or data change):
//
//   node scripts/bundle-engine.mjs
//
import { execSync } from "node:child_process";
import { cpSync, mkdirSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "..", ".."); // gui/scripts -> repo root
const build = resolve(repo, "build");
const cpp = resolve(repo, "cpp");
const dest = resolve(here, "..", "src-tauri", "resources", "engine");
const isWin = process.platform === "win32";
const exeName = isWin ? "simorgh.exe" : "simorgh";

function run(cmd, cwd) {
  console.log(`$ ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit" });
}

// 1. configure + build the engine (Release)
mkdirSync(build, { recursive: true });
const gen = isWin ? '-G "MinGW Makefiles"' : "";
if (!existsSync(resolve(build, "CMakeCache.txt")))
  run(`cmake ${gen} "${cpp}" -DCMAKE_BUILD_TYPE=Release`, build);
run("cmake --build . -j", build);

// 2. copy engine + data next to each other (engine loads data/ relative to cwd)
mkdirSync(resolve(dest, "data"), { recursive: true });
cpSync(resolve(build, exeName), resolve(dest, exeName));
for (const f of ["book.txt", "weights.txt", "openings.tsv"])
  cpSync(resolve(repo, "data", f), resolve(dest, "data", f));

console.log(`\nEngine bundled into ${dest}`);
