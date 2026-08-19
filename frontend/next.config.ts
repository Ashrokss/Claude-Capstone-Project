import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { NextConfig } from "next";

/**
 * Load the repository-root .env, which configures both services.
 *
 * Next only reads .env files from its own directory, and this app deliberately
 * keeps one file at the root instead. next.config runs before compilation, so
 * anything set here is visible when NEXT_PUBLIC_* values are inlined into the
 * bundle.
 *
 * Real environment variables always win, which is what makes this safe on
 * Netlify and in Docker: there is no .env there at all, the values arrive from
 * the platform, and this quietly does nothing.
 */
function loadRootEnv() {
  const file = resolve(process.cwd(), "..", ".env");
  if (!existsSync(file)) return;

  // Split on either line ending. A file written on Windows carries \r, which
  // is a line terminator to a JS regex — `.` will not match it and `$` will not
  // step over it, so splitting on "\n" alone silently parses nothing but the
  // final line.
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;

    const [, key, rawValue] = match;
    if (process.env[key] !== undefined) continue;

    process.env[key] = rawValue.trim().replace(/^["']|["']$/g, "");
  }
}

loadRootEnv();

// Netlify and Vercel each build their own serverless output and cannot consume
// a standalone bundle — setting it makes their adapters miss the server
// entirely. The Docker image, on the other hand, depends on it: the runtime
// stage copies .next/standalone and runs server.js with no node_modules.
// So the option follows whoever is doing the build.
const onManagedHost = Boolean(process.env.NETLIFY || process.env.VERCEL);

const nextConfig: NextConfig = {
  // Emits a self-contained server bundle with only the packages actually
  // imported, so the runtime image does not need node_modules at all.
  ...(onManagedHost ? {} : { output: "standalone" as const }),
};

export default nextConfig;
