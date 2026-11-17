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

export function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

/**
 * 把 /static/json/... 這個路徑轉給 cdn.nba.com 並回傳結果。
 * @returns {{status:number, body:string, headers:Object}}
 */
export async function proxyPath(path, origin) {
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
  let upstream;
  try {
    upstream = await fetch(url, {
      headers: {
        // cdn.nba.com 只認這個。沒有它一律 403。
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
        "Accept": "application/json, text/plain, */*",
      },
    });
  } catch (e) {
    return {
      status: 502,
      body: JSON.stringify({ error: "upstream fetch failed", detail: String(e && e.message) }),
      headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
    };
  }

  const body = await upstream.text();
  const secs = cacheSeconds(path);
  return {
    status: upstream.status,
    body,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": `public, max-age=${secs}, s-maxage=${secs}`,
      "X-Upstream-Status": String(upstream.status),
      ...corsHeaders(origin),
    },
  };
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
