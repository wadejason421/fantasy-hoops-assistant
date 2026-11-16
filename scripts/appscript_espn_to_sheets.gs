/**
 * NBA box score + play-by-play -> Google Sheets，純 Apps Script，不需要任何伺服器。
 *
 * 走 ESPN 的介面，因為它只檢查 User-Agent，不檢查 TLS 指紋 ——
 * 這是 Apps Script 唯一有機會走通的路（NBA 官方擋 TLS 指紋，UrlFetchApp 碰不到那一層）。
 *
 * 安裝：
 *   1. 開一個新的 Google Sheet -> 擴充功能 -> Apps Script，把這整份貼進去
 *   2. 先跑 testConnectivity()，看執行記錄確認通不通（30 秒）
 *   3. 通了就跑 setupTriggers()，之後它會自己跑
 *
 * 產生三個工作表：
 *   games          一場比賽一列（比分、單節、狀態）
 *   box_score      一個球員一列（14 項傳統數據）
 *   play_by_play   一個動作一列（含比分、投籃座標）
 *
 * 重複執行安全：以 ESPN 的 play id / (gameId+playerId) 為鍵去重，不會寫出重複列。
 */

// ============================== 設定 ==============================

var CHROME_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

var SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba';

// 要不要寫 play-by-play（一場約 500 列；八場比賽約 4000 列）
var WRITE_PBP = true;

// ============================== HTTP ==============================

function fetchJson_(url) {
  var res = UrlFetchApp.fetch(url, {
    headers: {'User-Agent': CHROME_UA},     // ← 關鍵：ESPN 會擋 Apps Script 的預設 UA
    muteHttpExceptions: true,
    followRedirects: true
  });
  var code = res.getResponseCode();
  if (code !== 200) {
    throw new Error('HTTP ' + code + ' ' + url + ' :: ' +
                    res.getContentText().substring(0, 200));
  }
  return JSON.parse(res.getContentText());
}

// ============================== 日期 ==============================

/** NBA 的「比賽日」以美東為準。回傳 yyyymmdd。 */
function etDateString_(daysAgo) {
  var d = new Date(new Date().getTime() - (daysAgo || 0) * 86400000);
  return Utilities.formatDate(d, 'America/New_York', 'yyyyMMdd');
}

// ============================== 工作表 ==============================

function sheet_(name, header) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

/** 讀出某一欄已有的值，用來去重。 */
function existingKeys_(sh, keyCol) {
  var last = sh.getLastRow();
  if (last < 2) return {};
  var vals = sh.getRange(2, keyCol, last - 1, 1).getValues();
  var set = {};
  for (var i = 0; i < vals.length; i++) set[String(vals[i][0])] = true;
  return set;
}

/** 一次寫入多列（不要用 appendRow 迴圈，會慢而且吃配額）。 */
function appendRows_(sh, rows) {
  if (!rows.length) return 0;
  sh.getRange(sh.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  return rows.length;
}

// ============================== 主流程 ==============================

var GAMES_HEADER = ['key', 'gameId', 'dateET', 'status', 'period', 'clock',
                    'away', 'awayScore', 'home', 'homeScore',
                    'awayQ', 'homeQ', 'fetchedAt'];

var BOX_HEADER = ['key', 'gameId', 'dateET', 'team', 'playerId', 'player', 'pos',
                  'starter', 'MIN', 'PTS', 'FG', '3PT', 'FT', 'REB', 'AST', 'TO',
                  'STL', 'BLK', 'OREB', 'DREB', 'PF', 'plusMinus', 'dnpReason'];

var PBP_HEADER = ['key', 'gameId', 'dateET', 'seq', 'period', 'clock', 'teamId',
                  'type', 'text', 'awayScore', 'homeScore', 'scoreValue',
                  'scoringPlay', 'shootingPlay', 'coordX', 'coordY', 'wallclock'];

/**
 * 抓某一天（美東）的所有已結束比賽。
 * daysAgo=1 是昨天，這是每天早上跑最合理的選擇（美東的比賽夜晚才打完）。
 */
function fetchDay(daysAgo) {
  var dateET = etDateString_(daysAgo == null ? 1 : daysAgo);
  var sb = fetchJson_(SITE + '/scoreboard?dates=' + dateET);
  var events = sb.events || [];
  Logger.log('%s：找到 %s 場比賽', dateET, events.length);

  var gSh = sheet_('games', GAMES_HEADER);
  var bSh = sheet_('box_score', BOX_HEADER);
  var pSh = WRITE_PBP ? sheet_('play_by_play', PBP_HEADER) : null;

  var gSeen = existingKeys_(gSh, 1);
  var bSeen = existingKeys_(bSh, 1);
  var pSeen = WRITE_PBP ? existingKeys_(pSh, 1) : {};

  var gRows = [], bRows = [], pRows = [];
  var now = new Date();

  for (var i = 0; i < events.length; i++) {
    var ev = events[i];
    var comp = ev.competitions[0];
    var st = comp.status.type;

    // 只處理已結束的比賽；進行中的留給 watchLive()
    if (st.name !== 'STATUS_FINAL') {
      Logger.log('  跳過 %s（%s）', ev.shortName, st.description);
      continue;
    }

    var detail;
    try {
      detail = fetchJson_(SITE + '/summary?event=' + ev.id);
    } catch (e) {
      Logger.log('  %s 抓取失敗：%s', ev.shortName, e.message);
      continue;
    }

    // ---- games ----
    var c = detail.header.competitions[0];
    var home = null, away = null;
    for (var k = 0; k < c.competitors.length; k++) {
      if (c.competitors[k].homeAway === 'home') home = c.competitors[k];
      else away = c.competitors[k];
    }
    var ls = function (t) {
      return (t.linescores || []).map(function (x) { return x.displayValue; }).join('/');
    };
    var gKey = ev.id;
    if (!gSeen[gKey]) {
      gRows.push([gKey, ev.id, dateET, st.description,
                  comp.status.period, comp.status.displayClock,
                  away.team.abbreviation, Number(away.score),
                  home.team.abbreviation, Number(home.score),
                  ls(away), ls(home), now]);
      gSeen[gKey] = true;
    }

    // ---- box score ----
    var teams = (detail.boxscore && detail.boxscore.players) || [];
    for (var t = 0; t < teams.length; t++) {
      var abbr = teams[t].team.abbreviation;
      var stat = teams[t].statistics[0];
      var ath = stat.athletes || [];
      for (var p = 0; p < ath.length; p++) {
        var A = ath[p];
        var pid = A.athlete.id;
        var bKey = ev.id + '-' + pid;
        if (bSeen[bKey]) continue;
        var s = A.stats || [];
        // 沒上場的球員 stats 是空陣列
        var row = [bKey, ev.id, dateET, abbr, pid, A.athlete.displayName,
                   (A.athlete.position || {}).abbreviation || '',
                   A.starter === true];
        for (var q = 0; q < 14; q++) row.push(s[q] == null ? '' : s[q]);
        row.push(A.didNotPlay ? (A.reason || 'DNP') : '');
        bRows.push(row);
        bSeen[bKey] = true;
      }
    }

    // ---- play by play ----
    if (WRITE_PBP) {
      var plays = detail.plays || [];
      for (var j = 0; j < plays.length; j++) {
        var pp = plays[j];
        if (pSeen[pp.id]) continue;
        var co = pp.coordinate || {};
        // ESPN 在非投籃事件會塞 int32 最小值當佔位，要濾掉
        var cx = (co.x == null || Math.abs(co.x) > 100000) ? '' : co.x;
        var cy = (co.y == null || Math.abs(co.y) > 100000) ? '' : co.y;
        pRows.push([pp.id, ev.id, dateET, Number(pp.sequenceNumber),
                    (pp.period || {}).number || '',
                    (pp.clock || {}).displayValue || '',
                    (pp.team || {}).id || '',
                    (pp.type || {}).text || '',
                    pp.text || '',
                    pp.awayScore, pp.homeScore, pp.scoreValue,
                    pp.scoringPlay === true, pp.shootingPlay === true,
                    cx, cy, pp.wallclock || '']);
        pSeen[pp.id] = true;
      }
    }

    Logger.log('  %s %s-%s %s  已排入', ev.shortName,
               away.score, home.score, st.description);
    Utilities.sleep(400);        // 對 ESPN 客氣一點
  }

  var n1 = appendRows_(gSh, gRows);
  var n2 = appendRows_(bSh, bRows);
  var n3 = WRITE_PBP ? appendRows_(pSh, pRows) : 0;
  Logger.log('寫入：games %s 列、box_score %s 列、play_by_play %s 列', n1, n2, n3);
  return {games: n1, box: n2, pbp: n3};
}

/** 每天早上跑這個：抓昨天（美東）的比賽。 */
function runDaily() {
  fetchDay(1);
}

/**
 * 比賽進行中跑這個（搭配「每 5 分鐘」觸發器）。
 * 它只更新 games 工作表的即時比分，不重複寫 box score ——
 * 完整資料等比賽結束後由 runDaily() 補齊。
 */
function watchLive() {
  var dateET = etDateString_(0);
  var sb = fetchJson_(SITE + '/scoreboard?dates=' + dateET);
  var live = (sb.events || []).filter(function (ev) {
    return ev.competitions[0].status.type.state === 'in';
  });
  if (!live.length) { Logger.log('%s：目前沒有進行中的比賽', dateET); return; }

  var sh = sheet_('live', ['updatedAt', 'gameId', 'matchup', 'period', 'clock',
                           'away', 'awayScore', 'home', 'homeScore']);
  var rows = [], now = new Date();
  for (var i = 0; i < live.length; i++) {
    var c = live[i].competitions[0], st = c.status;
    var h = null, a = null;
    for (var k = 0; k < c.competitors.length; k++) {
      if (c.competitors[k].homeAway === 'home') h = c.competitors[k]; else a = c.competitors[k];
    }
    rows.push([now, live[i].id, live[i].shortName, st.period, st.displayClock,
               a.team.abbreviation, Number(a.score),
               h.team.abbreviation, Number(h.score)]);
  }
  appendRows_(sh, rows);
  Logger.log('%s 場進行中，已更新', rows.length);
}

// ============================== 觸發器 ==============================

/** 建立觸發器：每天台北 14:00（美東前一天 01:00，所有比賽都打完了）抓昨天的資料。 */
function setupTriggers() {
  var existing = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existing.length; i++) {
    if (existing[i].getHandlerFunction() === 'runDaily') ScriptApp.deleteTrigger(existing[i]);
  }
  ScriptApp.newTrigger('runDaily').timeBased().atHour(14).everyDays(1).create();
  Logger.log('已建立觸發器：每天 14:00（指令碼時區）跑 runDaily()');
  Logger.log('時區請在「專案設定 -> 時區」確認是 Asia/Taipei');
}

function deleteTriggers() {
  var ts = ScriptApp.getProjectTriggers();
  for (var i = 0; i < ts.length; i++) ScriptApp.deleteTrigger(ts[i]);
  Logger.log('已刪除 %s 個觸發器', ts.length);
}

// ============================== 連通性測試 ==============================

/** 裝好之後先跑這個。30 秒內告訴你這條路通不通。 */
function testConnectivity() {
  Logger.log('=== 1. 你設的 User-Agent 有沒有真的送出去 ===');
  try {
    var echo = UrlFetchApp.fetch('https://httpbin.org/headers', {
      headers: {'User-Agent': CHROME_UA}, muteHttpExceptions: true});
    var sent = JSON.parse(echo.getContentText()).headers['User-Agent'];
    Logger.log('  伺服器收到的 UA：%s', sent);
    if (sent.indexOf('Google-Apps-Script') >= 0) {
      Logger.log('  ✗ Google 覆寫了 UA。ESPN 會因此回 403，這條路走不通。');
      Logger.log('    改用 .github/workflows/probe-nba.yml 的雲端方案。');
      return;
    }
    Logger.log('  ✓ UA 成功送出');
  } catch (e) {
    Logger.log('  echo 測試失敗：%s', e.message);
  }

  Logger.log('');
  Logger.log('=== 2. ESPN 三個端點 ===');
  var urls = [
    ['scoreboard', SITE + '/scoreboard?dates=' + etDateString_(1)],
    ['summary',    SITE + '/summary?event=401909993'],
    ['playbyplay', 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba' +
                   '/events/401909993/competitions/401909993/plays?limit=1000']
  ];
  var allOk = true;
  for (var i = 0; i < urls.length; i++) {
    try {
      var r = UrlFetchApp.fetch(urls[i][1], {headers: {'User-Agent': CHROME_UA},
                                             muteHttpExceptions: true});
      var code = r.getResponseCode();
      Logger.log('  %s  HTTP %s  %s bytes', urls[i][0], code,
                 r.getContentText().length);
      if (code !== 200) allOk = false;
    } catch (e) {
      Logger.log('  %s  THREW %s', urls[i][0], e.message);
      allOk = false;
    }
  }

  Logger.log('');
  Logger.log(allOk
    ? '✓ 全部通過。可以跑 fetchDay(1) 試抓一天，再跑 setupTriggers()。'
    : '✗ 有端點不通。403 代表 Google 的 IP 或 UA 被擋，改走雲端方案。');
}
