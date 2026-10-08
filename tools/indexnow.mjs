// 푸시 한 번에 "본문이 바뀐 페이지"만 골라 IndexNow(네이버·빙)로 알린다. (.github/workflows/indexnow.yml 이 돌린다)
//
//   node tools/indexnow.mjs <이전 커밋> [이번 커밋]           ← 바뀐 주소만 출력
//   node tools/indexnow.mjs <이전 커밋> [이번 커밋] --send    ← 배포 확인 후 전송
//   node tools/indexnow.mjs --urls /blog/suno-guide/ /pricing/ ← 주소를 직접 골라 전송
//
// 이 사이트는 HTML 을 저장소에 그대로 올리므로 빌드 없이 git 의 두 커밋을 비교한다.
// 메뉴·푸터·CSS 를 고치면 46페이지가 전부 바뀌므로 title + description + <main> 글자만 본다.
// 바뀐 게 40개를 넘으면 공통 틀을 고친 것으로 보고 새 페이지만 보낸다.
// 색인을 보장하지는 않는다. 구글은 IndexNow 를 받지 않는다.

import { execFileSync } from 'node:child_process';

const ORIGIN = 'https://ai.howtopackbook.com';
const KEY = 'eeddf7948fcc924a783d456c3c7afe31';
const MAX = 40;
const UA = 'Mozilla/5.0 (compatible; ai-howtopackbook-indexnow bot)';

const args = process.argv.slice(2);
const send = args.includes('--send') || args.includes('--urls');

function contentOf(html) {
  const title = (html.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || '';
  const desc = (html.match(/<meta name="description" content="([^"]*)"/) || [])[1] || '';
  const a = html.indexOf('<main');
  const b = html.indexOf('</main>', a);
  const main = a < 0 ? '' : html.slice(a, b < 0 ? undefined : b);
  const text = main
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return `${title}\n${desc}\n${text}`;
}

// 파일 → 운영 주소. Cloudflare Pages 는 x.html 을 /x 로 308 하므로 확장자를 뗀다.
function pathOf(file) {
  if (file === 'index.html') return '/';
  if (file.endsWith('/index.html')) return '/' + file.slice(0, -'index.html'.length);
  return '/' + file.replace(/\.html$/, '');
}

const git = (...a) => execFileSync('git', a, { encoding: 'utf8', maxBuffer: 64 << 20 });
const show = (rev, f) => {
  try {
    return execFileSync('git', ['show', `${rev}:${f}`], { encoding: 'utf8', maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'ignore'] });
  } catch { return null; }
};

let paths;
let probe = null;
if (args[0] === '--urls') {
  paths = args.slice(1);
} else {
  const revs = args.filter((x) => !x.startsWith('--'));
  const before = revs[0] || 'HEAD~1';
  const after = revs[1] || 'HEAD';
  const files = git('diff', '--name-only', '--diff-filter=AM', before, after, '--', '*.html')
    .split('\n').filter((f) => f && f !== '404.html' && !f.startsWith('tools/'));
  const changed = [];
  for (const f of files) {
    const prev = show(before, f);
    const now = show(after, f);
    if (now === null) continue;
    if (prev === null || contentOf(prev) !== contentOf(now)) {
      changed.push({ file: f, path: pathOf(f), isNew: prev === null, want: contentOf(now) });
    }
  }
  if (!changed.length) {
    console.log('본문이 바뀐 페이지가 없습니다 - 보내지 않습니다.');
    process.exit(0);
  }
  let pick = changed;
  if (changed.length > MAX) {
    pick = changed.filter((c) => c.isNew);
    console.log(`바뀐 페이지 ${changed.length}개 > ${MAX} - 공통 틀 변경으로 보고 새 페이지 ${pick.length}개만 보냅니다.`);
    if (!pick.length) process.exit(0);
  }
  console.log(`보낼 페이지 ${pick.length}개:`);
  for (const c of pick) console.log(`  ${c.isNew ? '[새 페이지] ' : ''}${c.path}`);
  paths = pick.map((c) => c.path);
  probe = pick[0];
}

if (!send) process.exit(0);

// 배포 확인 - Cloudflare Pages 가 새 버전을 낼 때까지 기다린다(최대 15분)
if (probe) {
  const url = ORIGIN + encodeURI(probe.path);
  const deadline = Date.now() + 15 * 60 * 1000;
  let live = false;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(url, { headers: { 'cache-control': 'no-cache', 'user-agent': UA } });
      if (r.status === 200 && contentOf(await r.text()) === probe.want) { live = true; break; }
    } catch {}
    await new Promise((ok) => setTimeout(ok, 20000));
  }
  if (!live) {
    console.error(`15분 안에 운영에 반영되지 않았습니다(${probe.path}) - 보내지 않습니다.`);
    process.exit(1);
  }
  console.log('운영 반영 확인.');
}

const host = new URL(ORIGIN).host;
const keyLocation = `${ORIGIN}/${KEY}.txt`;
const urlList = paths.map((p) => ORIGIN + encodeURI(p));

const keyRes = await fetch(keyLocation, { headers: { 'user-agent': UA } });
if (keyRes.status !== 200 || (await keyRes.text()).trim() !== KEY) {
  console.error(`키 파일 확인 실패 (${keyRes.status}) - 배포가 끝났는지 확인하세요: ${keyLocation}`);
  process.exit(1);
}
for (const u of urlList) {
  const r = await fetch(u, { method: 'HEAD', redirect: 'manual', headers: { 'user-agent': UA } });
  if (r.status !== 200) {
    console.error(`${r.status} ${decodeURI(u)} - 200 이 아닌 주소는 보내지 않습니다.`);
    process.exit(1);
  }
}

const endpoints = [
  ['네이버', 'https://searchadvisor.naver.com/indexnow'],
  ['IndexNow(빙 등)', 'https://api.indexnow.org/indexnow'],
];
let bad = 0;
for (const [name, url] of endpoints) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ host, key: KEY, keyLocation, urlList }),
  });
  // 200 = 받음, 202 = 받고 키 검증 대기. 둘 다 정상.
  const ok = res.status === 200 || res.status === 202;
  if (!ok) bad++;
  console.log(`${ok ? 'OK ' : 'ERR'} ${name} ${res.status} ${ok ? '' : (await res.text()).slice(0, 200)}`);
}
console.log(`보낸 주소 ${urlList.length}개:\n` + urlList.map((u) => '  ' + decodeURI(u)).join('\n'));
process.exit(bad ? 1 : 0);
