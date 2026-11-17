/**
 * NBA 即時代理的共用邏輯。Cloudflare Worker 與 Vercel 版本都用這一份。
 *
 * 為什麼需要代理：瀏覽器打 cdn.nba.com 會被 CORS 擋（實測從第三方網域 fetch
 * 直接 Failed to fetch）。代理在伺服器端抓（沒有 CORS 這回事），再加上
 * Access-Control-Allow-Origin 轉給前端。
 *
 * 為什麼可以免費：NBA 擋的是傳輸層指紋，而 JS runtime 的指紋被接受 ——
 * 實測 Node 原生 fetch 只要帶 Referer 就 200，住宅 IP 與 Azure 資料中心 IP 都成立。
 * 所以不需要編譯原生套件，任何免費 serverless 平台都跑得動。
 *
 * ⚠️ 白名單是必要的，不要做成開放代理 —— 否則會被拿去當跳板。
 */

const ALLOW = [
  // 今日比賽 + 即時比分
  /^\/static\/json\/liveData\/scoreboard\/todaysScoreboard_00\.json$/,
  // 單場 box score / play-by-play，game id 必須是 10 位數字
  /^\/static\/json\/liveData\/boxscore\/boxscore_\d{10}\.json$/,
  /^\/static\/json\/liveData\/playbyplay\/playbyplay_\d{10}\.json$/,
  // 整季賽程
  /^\/static\/json\/staticData\/scheduleLeagueV2_32\.json$/,
];

// 不同資料的快取秒數：比賽中的資料要短，賽程可以長
function cacheSeconds(path) {
  if (path.includes("/staticData/")) return 3600;   // 賽程：1 小時
  if (path.includes("todaysScoreboard")) return 10; // 今日比分：10 秒
  return 10;                                        // box score / pbp：10 秒
}

/**
 * 設了環境變數 PROXY_TOKEN 就要求每個請求帶上它
 * （header `X-Proxy-Token` 或 query `?token=`）。
 * 用等長時間比較，不要用 === —— 逐字元比較會從回應時間洩漏 token 內容。
 * 這個設計取自 scripts/nba_proxy.py。
 */
export function tokenOk(expected, got) {
  if (!expected) return true;              // 沒設就不檢查
  const a = String(expected), b = String(got || "");
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export function unauthorized(origin) {
  return {
    status: 401,
    body: JSON.stringify({ error: "unauthorized", detail: "缺少或錯誤的 X-Proxy-Token" }),
    headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
  };
}

export function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, If-Modified-Since, X-Proxy-Token",
    "Access-Control-Max-Age": "86400",
  };
}

/**
 * 把 /static/json/... 這個路徑轉給 cdn.nba.com 並回傳結果。
 * @returns {{status:number, body:string, headers:Object}}
 */
export async function proxyPath(path, origin, reqHeaders) {
  if (!ALLOW.some((re) => re.test(path))) {
    return {
      status: 403,
      body: JSON.stringify({
        error: "path not allowed",
        path,
        hint: "只開放 liveData 的 scoreboard / boxscore / playbyplay 與 staticData 的賽程",
      }),
      headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
    };
  }

  const url = `https://cdn.nba.com${path}`;
  const out = {
    // cdn.nba.com 只認這個。沒有它一律 403。
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
  };

  // 轉送條件式請求，讓沒變動的資料回 304（0 bytes）而不是整包重傳。
  // 實測 cdn.nba.com 支援 If-Modified-Since（If-None-Match 無效，所以不轉）。
  // 比賽中每 10 秒輪詢一次 play-by-play，這一行把每場的流量從
  // 約 200 MB 降到只有真正變動時才傳 —— 手機看球差很多。
  const ims = reqHeaders && (reqHeaders["if-modified-since"] || reqHeaders["If-Modified-Since"]);
  if (ims) out["If-Modified-Since"] = ims;

  let upstream;
  try {
    upstream = await fetch(url, { headers: out });
  } catch (e) {
    return {
      status: 502,
      body: JSON.stringify({ error: "upstream fetch failed", detail: String(e && e.message) }),
      headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
    };
  }

  const secs = cacheSeconds(path);
  const lastMod = upstream.headers.get("last-modified");

  const headers = {
    "Cache-Control": `public, max-age=${secs}, s-maxage=${secs}`,
    "X-Upstream-Status": String(upstream.status),
    // 要讓前端讀得到 Last-Modified，必須明確 expose（CORS 預設只給少數幾個 header）
    "Access-Control-Expose-Headers": "Last-Modified, X-Upstream-Status",
    ...corsHeaders(origin),
  };
  if (lastMod) headers["Last-Modified"] = lastMod;

  // 304 不能有 body
  if (upstream.status === 304) return { status: 304, body: "", headers };

  headers["Content-Type"] = "application/json; charset=utf-8";
  return { status: upstream.status, body: await upstream.text(), headers };
}

/** GET / 回這個，方便確認部署成功與白名單內容。 */
export function indexPayload(base) {
  return {
    ok: true,
    what: "NBA liveData CORS proxy",
    usage: `${base}/static/json/liveData/scoreboard/todaysScoreboard_00.json`,
    allowed: [
      "/static/json/liveData/scoreboard/todaysScoreboard_00.json",
      "/static/json/liveData/boxscore/boxscore_<10位gameId>.json",
      "/static/json/liveData/playbyplay/playbyplay_<10位gameId>.json",
      "/static/json/staticData/scheduleLeagueV2_32.json",
    ],
    cache: { live: "10s", schedule: "3600s" },
  };
}
