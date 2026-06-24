/** @type {import('next').NextConfig} */
const nextConfig = {
  // The shared contracts package ships TypeScript source; let Next transpile it.
  transpilePackages: ["@tickertea/contracts"],
  webpack: (config) => {
    // Our code uses ESM-style ".js" specifiers that point at ".ts" sources
    // (e.g. import "./repository.js"). Teach webpack to resolve them to TS files.
    config.resolve.extensionAlias = {
      ".js": [".ts", ".tsx", ".js"],
      ".mjs": [".mts", ".mjs"],
    };
    return config;
  },
};

export default nextConfig;
