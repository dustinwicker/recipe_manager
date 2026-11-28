const SHEET_ID = '19ZdDKmPG1oNI3NK2xqa1uRjyBYfGG-K3rOV4phIgIPk';

function sheet_() {
  const spreadsheet = SpreadsheetApp.openById(SHEET_ID);
  let activity = spreadsheet.getSheetByName('activity');
  if (!activity) {
    activity = spreadsheet.insertSheet('activity');
    activity.appendRow(['title', 'visits', 'searches', 'linkClicks', 'lastAt']);
  }
  return activity;
}

function readAll_() {
  const values = sheet_().getDataRange().getValues();
  const counts = {};
  for (let index = 1; index < values.length; index += 1) {
    const title = String(values[index][0] || '').trim();
    if (!title || title === 'title') continue;
    counts[title] = {
      visits: Number(values[index][1]) || 0,
      searches: Number(values[index][2]) || 0,
      linkClicks: Number(values[index][3]) || 0,
      lastAt: Number(values[index][4]) || 0
    };
  }
  return counts;
}

function writeAll_(counts) {
  const activity = sheet_();
  const rows = [['title', 'visits', 'searches', 'linkClicks', 'lastAt']];
  Object.keys(counts).sort(function (left, right) {
    return left.toLowerCase().localeCompare(right.toLowerCase());
  }).forEach(function (title) {
    const row = counts[title] || {};
    rows.push([
      title,
      Number(row.visits) || 0,
      Number(row.searches) || 0,
      Number(row.linkClicks) || 0,
      Number(row.lastAt) || 0
    ]);
  });
  activity.clear();
  activity.getRange(1, 1, rows.length, 5).setValues(rows);
}

function merge_(incoming) {
  const counts = readAll_();
  Object.keys(incoming || {}).forEach(function (title) {
    const saved = counts[title] || { visits: 0, searches: 0, linkClicks: 0, lastAt: 0 };
    const next = incoming[title] || {};
    counts[title] = {
      visits: Math.max(saved.visits || 0, Number(next.visits) || 0),
      searches: Math.max(saved.searches || 0, Number(next.searches) || 0),
      linkClicks: Math.max(saved.linkClicks || 0, Number(next.linkClicks) || 0),
      lastAt: Math.max(saved.lastAt || 0, Number(next.lastAt) || 0)
    };
  });
  writeAll_(counts);
  return counts;
}

function record_(title, kind) {
  const counts = readAll_();
  const row = counts[title] || { visits: 0, searches: 0, linkClicks: 0, lastAt: 0 };
  if (kind === 'search') row.searches = (Number(row.searches) || 0) + 1;
  else if (kind === 'link') row.linkClicks = (Number(row.linkClicks) || 0) + 1;
  else row.visits = (Number(row.visits) || 0) + 1;
  row.lastAt = Date.now();
  counts[title] = row;
  writeAll_(counts);
  return counts;
}

function respond_(counts) {
  return ContentService
    .createTextOutput(JSON.stringify(counts))
    .setMimeType(ContentService.MimeType.JSON);
}

function handle_(body) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    if (body.action === 'record' && body.title) return record_(String(body.title), body.kind || 'visit');
    if (body.action === 'sync') return merge_(body.activity || {});
    return readAll_();
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return respond_(handle_({ action: 'list' }));
}

function doPost(event) {
  let body = {};
  try {
    body = JSON.parse((event.postData && event.postData.contents) || '{}');
  } catch (error) {
    body = {};
  }
  return respond_(handle_(body));
}
