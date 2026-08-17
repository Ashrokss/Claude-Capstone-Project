import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a self-contained server bundle with only the packages actually
  // imported, so the runtime image does not need node_modules at all.
  output: "standalone",
};

export default nextConfig;
