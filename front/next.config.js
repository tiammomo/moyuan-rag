const publicApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const internalApiUrl = process.env.INTERNAL_API_URL || publicApiUrl;

function toRemotePattern(urlString) {
  try {
    const url = new URL(urlString);
    return {
      protocol: url.protocol.replace(':', ''),
      hostname: url.hostname,
      port: url.port,
      pathname: '/**',
    };
  } catch {
    return null;
  }
}

const remotePatterns = [publicApiUrl, internalApiUrl]
  .map(toRemotePattern)
  .filter(Boolean)
  .filter((pattern, index, items) => {
    return (
      items.findIndex(
        (item) =>
          item.protocol === pattern.protocol &&
          item.hostname === pattern.hostname &&
          item.port === pattern.port &&
          item.pathname === pattern.pathname
      ) === index
    );
  });

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: publicApiUrl,
  },
  images: {
    remotePatterns,
  },
  async redirects() {
    return [
      {
        source: '/',
        destination: '/chat',
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${internalApiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
