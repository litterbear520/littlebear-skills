/** @type {import('next').NextConfig} */
const nextConfig = {
  // Reports are read from local JSON at build time and pre-rendered to static
  // HTML — no server runtime needed, which keeps us on Vercel's free tier.
  reactStrictMode: true,
};

export default nextConfig;
