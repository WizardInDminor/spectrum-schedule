/** @type {import('next').NextConfig} */
const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig = {
  // In dev the Next server proxies /api/* to the FastAPI service, mirroring the
  // Caddy layout in production so the browser only ever talks to one origin.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/:path*` }];
  },
};

export default nextConfig;
