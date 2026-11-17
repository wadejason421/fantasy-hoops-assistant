/**
 * Cloudflare Workers 版本。
 *
 * 部署（免費，每天 10 萬次請求）：
 *   1. npm i -g wrangler && wrangler login
 *   2. cd proxy && wrangler deploy
 *   會得到 https://nba-proxy.<你的名字>.workers.dev
 *
 * ⚠️ Workers 用的是 workerd，不是 Node —— 它的傳輸層指紋沒驗證過。
 *    部署後先打根路徑 /__selftest 確認；若回 upstream 403，
 *    改用 Vercel 版本（proxy/api/nba.js，跑真正的 Node，指紋已實測可用）。
 */
import { proxyPath, corsHeaders, indexPayload, tokenOk, unauthorized } from "./_shared.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "*";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "GET") {
      return new Response("method not allowed", { status: 405, headers: corsHeaders(origin) });
    }

    if (url.pathname === "/" || url.pathname === "") {
      return Response.json(indexPayload(url.origin), { headers: corsHeaders(origin) });
    }

    // 自我檢測：確認這個 runtime 的指紋過不過得了 NBA
    if (url.pathname === "/__selftest") {
      const r = await proxyPath("/static/json/liveData/scoreboard/todaysScoreboard_00.json", origin, {});
      let games = null;
      try { games = JSON.parse(r.body).scoreboard.games.length; } catch {}
      return Response.json({
        runtime: "cloudflare-workers",
        upstreamStatus: r.status,
        ok: r.status === 200 && games !== null,
        games,
        verdict: r.status === 200
          ? "workerd 的指紋可以通過，這個平台可用"
          : "workerd 被擋，改用 Vercel 版本（真 Node）",
      }, { headers: corsHeaders(origin) });
    }

    const token = request.headers.get("X-Proxy-Token") || url.searchParams.get("token");
    if (!tokenOk(env && env.PROXY_TOKEN, token)) {
      const u = unauthorized(origin);
      return new Response(u.body, { status: u.status, headers: u.headers });
    }
    const h = {}; request.headers.forEach((v, k) => (h[k.toLowerCase()] = v));
    const r = await proxyPath(url.pathname, origin, h);
    return new Response(r.body, { status: r.status, headers: r.headers });
  },
};
