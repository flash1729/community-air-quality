import { NextRequest } from "next/server";

export const maxDuration = 60;

const BASE = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = new URL(`${BASE}/api/v1/${path.join("/")}`);
  target.search = request.nextUrl.search;
  try {
    const response = await fetch(target, {
      method: request.method,
      cache: "no-store",
      headers: { accept: "application/json" },
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      { detail: "The air quality API is not reachable." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
