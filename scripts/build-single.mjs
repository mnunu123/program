// 여러 파일로 나뉜 앱을 한 파일로 묶는다.
//  dist/index.html    : 더블클릭으로 열리는 단일 HTML (인터넷 없이도 동작, 폰트만 온라인)
//  dist/artifact.html : claude.ai 아티팩트 게시용 (doctype/html/head/body 태그 없이)
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');
const safeJs = (s) => s.replace(/<\/script/gi, '<\\/script');

const html = read('index.html');
const css = read('assets/style.css');
const scripts = [
  'assets/data/guide.js', 'assets/data/knowledge.js', 'assets/data/tasks.js',
  'assets/data/drills.js', 'assets/data/essay.js', 'assets/app.js'
].map((p) => `/* ${p} */\n` + safeJs(read(p))).join('\n');

const body = html.split('<!--APP-START-->')[1].split('<!--APP-END-->')[0].trim();
const title = (html.match(/<title>([^<]*)<\/title>/) || [])[1] || '하이닉스 1차 대비 노트';
const fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">';

mkdirSync(join(root, 'dist'), { recursive: true });

const standalone = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${title}</title>
${fonts}
<style>
${css}
</style>
</head>
<body>
${body}
<script>
${scripts}
</script>
</body>
</html>
`;
writeFileSync(join(root, 'dist/index.html'), standalone);

const artifact = `<title>${title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
${fonts}
<style>
${css}
</style>
${body}
<script>
${scripts}
</script>
`;
writeFileSync(join(root, 'dist/artifact.html'), artifact);

const kb = (s) => (Buffer.byteLength(s) / 1024).toFixed(0) + 'KB';
console.log('dist/index.html', kb(standalone));
console.log('dist/artifact.html', kb(artifact));
