/**
 * Google Apps Script 可行性測試 —— 貼進 script.google.com 執行 testAll()，看執行記錄。
 *
 * 為什麼需要這支：本機已確認 NBA 官方介面擋的是 TLS 指紋，要用 curl_cffi 偽裝才通。
 * Apps Script 的 UrlFetchApp 無法控制 TLS 層，而且從 Google 的 IP 出去。
 * 這兩個變數只有在 Apps Script 裡實際跑一次才知道結果。
 *
 * 看三件事：
 *   1. echo  -> 你設的 User-Agent 到底有沒有送出去（Google 可能忽略它）
 *   2. nba*  -> NBA 官方介面通不通
 *   3. espn* -> ESPN 介面通不通（本機實測：ESPN 會擋 Apps Script 的預設 UA，
 *               改成瀏覽器 UA 就 200。所以這裡跑「預設」和「瀏覽器 UA」兩種）
 */

var CHROME_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

var GAME_ID = '0022600244';        // NBA 官方 id：2026-11-15 OKC @ SAC
var ESPN_ID = '401909993';         // 同一場比賽的 ESPN id

function probe_(label, url, headers) {
  var opts = {muteHttpExceptions: true, followRedirects: true};
  if (headers) opts.headers = headers;
  try {
    var t0 = new Date().getTime();
    var res = UrlFetchApp.fetch(url, opts);
    var ms = new Date().getTime() - t0;
    var code = res.getResponseCode();
    var body = res.getContentText();
    Logger.log('%s  ->  HTTP %s  %s bytes  %sms', label, code, body.length, ms);
    if (code !== 200) Logger.log('      body: %s', body.substring(0, 160));
    return {code: code, body: body};
  } catch (e) {
    Logger.log('%s  ->  THREW  %s', label, e.message);
    return null;
  }
}

function testAll() {
  Logger.log('=== 1. 確認 User-Agent 有沒有真的送出去 ===');
  var echo = probe_('echo (設瀏覽器 UA)', 'https://httpbin.org/headers',
                    {'User-Agent': CHROME_UA});
  if (echo && echo.code === 200) {
    var sent = JSON.parse(echo.body).headers['User-Agent'];
    Logger.log('      伺服器實際收到的 UA: %s', sent);
    Logger.log(sent.indexOf('Google-Apps-Script') >= 0
      ? '      => Google 覆寫了你的 UA。這條路沒救，往下看 ESPN 也別期待。'
      : '      => UA 有成功送出。');
  }

  Logger.log('');
  Logger.log('=== 2. NBA 官方介面 ===');
  var nbaHeaders = {
    'User-Agent': CHROME_UA,
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com'
  };
  probe_('nba todaysScoreboard',
    'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json', nbaHeaders);
  probe_('nba boxscore',
    'https://cdn.nba.com/static/json/liveData/boxscore/boxscore_' + GAME_ID + '.json', nbaHeaders);
  probe_('nba playbyplay',
    'https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_' + GAME_ID + '.json', nbaHeaders);

  Logger.log('');
  Logger.log('=== 3. ESPN 介面（預設 UA vs 瀏覽器 UA）===');
  var sb  = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261115';
  var sum = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=' + ESPN_ID;
  var pbp = 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/' +
            ESPN_ID + '/competitions/' + ESPN_ID + '/plays?limit=1000';

  probe_('espn scoreboard  (預設 UA)', sb, null);
  probe_('espn scoreboard  (瀏覽器UA)', sb, {'User-Agent': CHROME_UA});
  probe_('espn summary     (瀏覽器UA)', sum, {'User-Agent': CHROME_UA});
  var p = probe_('espn playbyplay  (瀏覽器UA)', pbp, {'User-Agent': CHROME_UA});
  if (p && p.code === 200) {
    Logger.log('      解析出 %s 筆 plays', JSON.parse(p.body).items.length);
  }

  Logger.log('');
  Logger.log('=== 怎麼讀這份結果 ===');
  Logger.log('NBA 三項都 200           -> 官方那條路在 Apps Script 可用，直接做');
  Logger.log('NBA 403 但 ESPN 200      -> Apps Script 只能走 ESPN（沒有投籃 x/y 座標）');
  Logger.log('兩邊都 403               -> Google 的 IP 被擋，改成 Mac 抓完寫進 Sheets');
}
