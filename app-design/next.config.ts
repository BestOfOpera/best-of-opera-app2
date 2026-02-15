import type { NextConfig } from "next";

const CURADORIA_API = process.env.CURADORIA_API_URL || "http://localhost:8002";
const REDATOR_API = process.env.REDATOR_API_URL || "http://localhost:8000";
const EDITOR_API = process.env.EDITOR_API_URL || "http://localhost:8001";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/curadoria/:path*", destination: `${CURADORIA_API}/api/:path*` },
      { source: "/api/redator/:path*", destination: `${REDATOR_API}/api/:path*` },
      { source: "/api/editor/:path*", destination: `${EDITOR_API}/api/v1/editor/:path*` },
    ];
  },
};

export default nextConfig;
