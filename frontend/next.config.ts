import type { NextConfig } from "next";

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
