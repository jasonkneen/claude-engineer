import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Start the WebSocket server
const wsServer = spawn(
  "node",
  ["--loader", "ts-node/esm", "server/memory-server.ts"],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      TS_NODE_PROJECT: join(__dirname, "server/tsconfig.json"),
    },
  }
);

// Start the Vite dev server
const viteServer = spawn("npm", ["run", "dev"], {
  stdio: "inherit",
});

// Handle process termination
process.on("SIGINT", () => {
  console.log("\nShutting down servers...");
  wsServer.kill();
  viteServer.kill();
  process.exit(0);
});

// Handle server process errors
wsServer.on("error", (error) => {
  console.error("WebSocket server error:", error);
});

viteServer.on("error", (error) => {
  console.error("Vite server error:", error);
});

// Handle server process exit
wsServer.on("exit", (code) => {
  console.log(`WebSocket server exited with code ${code}`);
  viteServer.kill();
  process.exit(code);
});

viteServer.on("exit", (code) => {
  console.log(`Vite server exited with code ${code}`);
  wsServer.kill();
  process.exit(code);
});
