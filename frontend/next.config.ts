import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "react-syntax-highlighter",
    ],
  },
};

export default nextConfig;