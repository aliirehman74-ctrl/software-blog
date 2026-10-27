/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",          // static HTML export -> works on Vercel free tier
  trailingSlash: true,
  images: { unoptimized: true },
};
export default nextConfig;
