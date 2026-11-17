/**
 * Vercel（Node runtime）版本 —— 指紋已實測可用，住宅 IP 與 Azure 都通。
 *
 * 部署（免費）：
 *   1. npm i -g vercel
 *   2. cd proxy && vercel --prod
 *   會得到 https://<專案名>.vercel.app
 *
 * 路由：vercel.json 把所有路徑導到這支，原始路徑在 req.url。
 */
import { proxyPath, corsHeaders, indexPayload, tokenOk, unauthorized } from "../_shared.js";

export default async function handler(req, res) {
  const origin = req.headers.origin || "*";
  const cors = corsHeaders(origin);

  if (req.method === "OPTIONS") {
    Object.entries(cors).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(204).end();
  }
  if (req.method !== "GET") {
    Object.entries(cors).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(405).send("method not allowed");
  }

  const path = (req.url || "/").split("?")[0];
  const base = `https://${req.headers.host}`;

  if (path === "/" || path === "/api/nba") {
    Object.entries(cors).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(200).json(indexPayload(base));
  }

  if (path === "/__selftest") {
    const r = await proxyPath("/static/json/liveData/scoreboard/todaysScoreboard_00.json", origin, {});
    let games = null;
    try { games = JSON.parse(r.body).scoreboard.games.length; } catch {}
    Object.entries(cors).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(200).json({
      runtime: `node ${process.version}`,
      upstreamStatus: r.status,
      ok: r.status === 200 && games !== null,
      games,
    });
  }

  const token = req.headers["x-proxy-token"] ||
                new URL(req.url, base).searchParams.get("token");
  if (!tokenOk(process.env.PROXY_TOKEN, token)) {
    const un = unauthorized(origin);
    Object.entries(un.headers).forEach(([k, v]) => res.setHeader(k, v));
    return res.status(401).send(un.body);
  }
  const r = await proxyPath(path, origin, req.headers);
  Object.entries(r.headers).forEach(([k, v]) => res.setHeader(k, v));
  return r.status === 304 ? res.status(304).end() : res.status(r.status).send(r.body);
}
