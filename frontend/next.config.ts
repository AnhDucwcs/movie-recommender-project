import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  allowedDevOrigins: ["192.168.110.156", "localhost", "127.0.0.1"],
};

export default nextConfig;
