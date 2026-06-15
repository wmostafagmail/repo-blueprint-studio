import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { createServer } from "node:http";

const PORT = Number(process.env.MOBILE_PREVIEW_PORT || 4173);
const API_ORIGIN = process.env.MOBILE_PREVIEW_API_ORIGIN || "http://127.0.0.1:8000";
const DIST_DIR = join(process.cwd(), "frontend", "dist");

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

function sendFile(response, filePath) {
  const extension = extname(filePath).toLowerCase();
  response.writeHead(200, {
    "Content-Type": MIME_TYPES[extension] || "application/octet-stream",
    "Cache-Control": extension === ".html" ? "no-cache" : "public, max-age=300",
  });
  createReadStream(filePath).pipe(response);
}

async function proxyApi(request, response) {
  const url = new URL(request.url, API_ORIGIN);
  const headers = new Headers();
  for (const [key, value] of Object.entries(request.headers)) {
    if (typeof value === "string" && key.toLowerCase() !== "host") {
      headers.set(key, value);
    }
  }

  const upstreamResponse = await fetch(url, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request,
    duplex: "half",
  });

  const responseHeaders = {};
  upstreamResponse.headers.forEach((value, key) => {
    responseHeaders[key] = value;
  });

  response.writeHead(upstreamResponse.status, responseHeaders);
  if (upstreamResponse.body) {
    for await (const chunk of upstreamResponse.body) {
      response.write(chunk);
    }
  }
  response.end();
}

function resolveStaticPath(urlPath) {
  const sanitizedPath = normalize(decodeURIComponent(urlPath)).replace(/^(\.\.[/\\])+/, "");
  const requestedPath = join(DIST_DIR, sanitizedPath);
  if (existsSync(requestedPath) && statSync(requestedPath).isFile()) {
    return requestedPath;
  }
  return join(DIST_DIR, "index.html");
}

const server = createServer(async (request, response) => {
  try {
    if (!request.url) {
      response.writeHead(400);
      response.end("Missing request URL");
      return;
    }

    if (request.url.startsWith("/api")) {
      await proxyApi(request, response);
      return;
    }

    const pathname = new URL(request.url, "http://localhost").pathname;
    const filePath = resolveStaticPath(pathname === "/" ? "/index.html" : pathname);
    sendFile(response, filePath);
  } catch (error) {
    response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    response.end(`Mobile preview server error: ${error.message}`);
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Mobile preview server listening on http://127.0.0.1:${PORT}`);
});
