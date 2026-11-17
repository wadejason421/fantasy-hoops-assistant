/**
 * 測：Node 原生 fetch（undici）能不能直接打 NBA 官方，不用任何 TLS 偽裝。
 *
 * 住宅 IP 實測結果（2026-11-17）：
 *   curl + 完整 header   -> 403
 *   Python + 完整 header -> 403
 *   Node fetch + Referer -> 200   ← undici 的指紋本身就被接受
 *
 * 要回答的是：資料中心 IP（GitHub Actions）上也成立嗎？
 * 成立的話，任何免費的 Node serverless 平台都能當即時 CORS 代理 ——
 * 不需要 curl_cffi、不需要編譯原生套件、不需要付費常駐伺服器。
 *
 * 結束碼 0 = cdn.nba.com 全通
 */
const CDN = "https://cdn.nba.com/static/json";
const STATS = "https://stats.nba.com/stats";
const G = process.argv[2] || "0022600244";

// cdn.nba.com 只需要 Referer。其他是保險。
const H = {
  "Referer": "https://www.nba.com/",
  "Origin": "https://www.nba.com",
  "Accept": "application/json, text/plain, */*",
};
const SH = { ...H, "x-nba-stats-origin": "stats", "x-nba-stats-token": "true" };

const rng = "&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0";

const checks = {
  "cdn todaysScoreboard": [`${CDN}/liveData/scoreboard/todaysScoreboard_00.json`, H,
    j => `${j.scoreboard.games.length} 場, gameDate=${j.scoreboard.gameDate}`],
  "cdn boxscore": [`${CDN}/liveData/boxscore/boxscore_${G}.json`, H,
    j => { const g = j.game;
      if (g.homeTeam.players.length < 10) throw new Error("球員數異常");
      return `${g.awayTeam.teamTricode} ${g.awayTeam.score} @ ${g.homeTeam.teamTricode} ${g.homeTeam.score}`; }],
  "cdn playbyplay": [`${CDN}/liveData/playbyplay/playbyplay_${G}.json`, H,
    j => { const a = j.game.actions;
      if (a.length < 400) throw new Error(`actions 只有 ${a.length}`);
      const s = a.filter(x => x.isFieldGoal && x.x != null).length;
      return `${a.length} actions, ${s} 筆有座標`; }],
  "cdn scheduleLeagueV2": [`${CDN}/staticData/scheduleLeagueV2_32.json`, H,
    j => `${j.leagueSchedule.gameDates.length} 個比賽日`],
  "stats boxscoreadvancedv3": [`${STATS}/boxscoreadvancedv3?GameID=${G}${rng}`, SH,
    j => `${j.boxScoreAdvanced.homeTeam.players.length} 名球員`],
  "stats hustlestatsboxscore": [`${STATS}/hustlestatsboxscore?GameID=${G}`, SH,
    j => `${j.resultSets.find(r => r.name === "PlayerStats").rowSet.length} 列`],
};

let ip = "(取不到)";
try {
  const r = await fetch("https://ipinfo.io/json");
  const j = await r.json();
  ip = `${j.ip} · ${j.city}, ${j.country} · ${j.org}`;
} catch {}

console.log("=".repeat(76));
console.log("Node 原生 fetch 探針（無 TLS 偽裝）");
console.log("=".repeat(76));
console.log(`node     : ${process.version}`);
console.log(`出口 IP  : ${ip}`);
console.log(`game id  : ${G}\n`);

const results = {};
for (const [name, [url, headers, check]] of Object.entries(checks)) {
  const t0 = Date.now();
  try {
    const r = await fetch(url, { headers });
    const ms = Date.now() - t0;
    if (r.status !== 200) { console.log(`  FAIL  ${name.padEnd(26)} HTTP ${r.status} (${ms}ms)`); results[name] = false; continue; }
    const txt = await r.text();
    let detail;
    try { detail = check(JSON.parse(txt)); }
    catch (e) { console.log(`  FAIL  ${name.padEnd(26)} 200 但內容不合: ${e.message}`); results[name] = false; continue; }
    console.log(`  PASS  ${name.padEnd(26)} ${detail} · ${txt.length.toLocaleString()}B · ${ms}ms`);
    results[name] = true;
  } catch (e) {
    console.log(`  FAIL  ${name.padEnd(26)} ${e.name}: ${String(e.message).slice(0, 50)} (${Date.now() - t0}ms)`);
    results[name] = false;
  }
  await new Promise(r => setTimeout(r, 400));
}

const cdnOk = Object.entries(results).filter(([k]) => k.startsWith("cdn")).every(([, v]) => v);
const statsOk = Object.entries(results).filter(([k]) => k.startsWith("stats")).every(([, v]) => v);

console.log("\n" + "=".repeat(76));
console.log(cdnOk
  ? "結論：Node 原生 fetch 可以直接抓 NBA 官方 —— 不需要 curl_cffi"
  : "結論：Node 原生 fetch 在這個 IP 不行");
console.log(`cdn.nba.com ${cdnOk ? "可用" : "不可用"} ／ stats.nba.com ${statsOk ? "可用" : "不可用"}`);
if (cdnOk) console.log("=> 任何支援 Node 的免費 serverless 平台都能當即時 CORS 代理");
console.log("=".repeat(76));

if (process.env.GITHUB_STEP_SUMMARY) {
  const fs = await import("node:fs");
  const rows = Object.entries(results).map(([k, v]) => `| \`${k}\` | ${v ? "✅" : "❌"} |`).join("\n");
  fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    `# Node 原生 fetch 探針\n\n**${cdnOk ? "cdn.nba.com 可用 — 不需要 curl_cffi" : "cdn.nba.com 不可用"}**\n\n` +
    `- node: \`${process.version}\`\n- 出口 IP: \`${ip}\`\n\n| 端點 | 結果 |\n|---|---|\n${rows}\n`);
}

process.exit(cdnOk ? 0 : 1);
