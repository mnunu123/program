/* 하이닉스 1차 예선 대비 – 앱 로직 (빌드 도구 없이 동작하는 단일 스크립트) */
(function () {
  'use strict';

  // ---------------------------------------------------------------- 유틸
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n) => Number(n).toLocaleString('ko-KR');
  const pad = (n) => String(n).padStart(2, '0');
  const mmss = (ms) => { const t = Math.max(0, Math.round(ms / 1000)); return `${pad(Math.floor(t / 60))}:${pad(t % 60)}`; };
  const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥'];

  const store = {
    get(k, d) { try { const v = localStorage.getItem('hxprep:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('hxprep:' + k, JSON.stringify(v)); } catch (e) { /* 저장 불가 환경 */ } },
    del(k) { try { localStorage.removeItem('hxprep:' + k); } catch (e) { /* noop */ } }
  };

  const DEFAULTS = {
    provider: 'none', apiKey: '', model: '',
    turns: 10, cooldown: 30, attachCap: 20000, charCap: 1000,
    clearAttach: true, keepHistory: true, copyLock: true, noTimer: false
  };
  const S = () => Object.assign({}, DEFAULTS, store.get('settings', {}));

  function estTokens(s) {
    let h = 0, a = 0, p = 0, w = 0;
    for (const ch of String(s)) {
      const c = ch.codePointAt(0);
      if (c >= 0xac00 && c <= 0xd7a3) h++;
      else if (c < 128 && /[A-Za-z0-9]/.test(ch)) a++;
      else if (/\s/.test(ch)) w++;
      else p++;
    }
    return Math.ceil(h + a / 3 + p * 0.7 + w * 0.2);
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }

  async function copyText(text, btn) {
    const done = () => { if (btn) { const o = btn.textContent; btn.textContent = '복사됨'; setTimeout(() => { btn.textContent = o; }, 1400); } };
    try { await navigator.clipboard.writeText(text); done(); return; } catch (e) { /* 아래 대체 경로 */ }
    const ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('복사가 막힌 환경이에요. 텍스트를 직접 선택해서 복사하세요.'); }
    ta.remove();
  }

  let toastTimer = null;
  function toast(msg) {
    let t = $('#toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
  }

  // ---------------------------------------------------------------- 데이터
  const K = window.KNOWLEDGE || [];
  const KMAP = Object.fromEntries(K.map((q) => [q.id, q]));
  const TASKS = window.TASKS || [];
  const TMAP = Object.fromEntries(TASKS.map((t) => [t.id, t]));
  const G = window.GUIDE || {};
  const ESSAYS = window.ESSAYS || [];
  const VD = window.VERIFY_DRILLS || [];
  const PD = window.PROMPT_DRILLS || [];

  // ---------------------------------------------------------------- 상태
  const state = { exam: null, result: null, drill: null, essay: null, popover: null, confirm: null, sol: null };
  let ticker = null;

  const NAV = [
    { g: '시작', items: [['home', '홈'], ['info', '시험 정보'], ['checklist', '전날·당일 체크리스트']] },
    { g: '유형별 가이드', items: [['guide-mc', '객관식 · O/X'], ['guide-short', '단답형'], ['guide-task', 'AI 과제형'], ['guide-essay', '서술형'], ['templates', '프롬프트 템플릿']] },
    { g: '실전 연습', items: [['mock-knowledge', '지식평가 모의고사'], ['mock-task', '활용평가 모의고사'], ['essay', '서술형 모의'], ['drill-verify', 'AI 답변 검증 드릴'], ['drill-prompt', '프롬프트 판단 드릴'], ['solutions', '정답·풀이 가이드']] },
    { g: '정리', items: [['cheat', '개념 치트시트'], ['case', '넥슨 시험 복기'], ['notes', '오답노트'], ['settings', '설정 · AI 연결']] }
  ];

  const route = () => { const h = (location.hash || '').replace(/^#/, ''); return h || 'home'; };

  // ---------------------------------------------------------------- 렌더 진입점
  function render() {
    const view = $('#view');
    document.body.classList.toggle('in-exam', !!state.exam);
    if (state.exam) { view.innerHTML = state.exam.kind === 'knowledge' ? viewKExam() : viewTExam(); afterExamRender(); return; }
    stopTicker();
    if (state.result) { view.innerHTML = state.result.kind === 'knowledge' ? viewKResult() : viewTResult(); window.scrollTo(0, 0); return; }
    renderNav();
    const r = route();
    const pages = {
      home: viewHome, info: () => page(G.info), checklist: viewChecklist,
      'guide-mc': () => page(G.mc), 'guide-short': () => page(G.short), 'guide-task': () => page(G.task), 'guide-essay': () => page(G.essay),
      templates: viewTemplates, 'mock-knowledge': viewKMenu, 'mock-task': viewTMenu, essay: viewEssay,
      'drill-verify': () => viewDrill('verify'), 'drill-prompt': () => viewDrill('prompt'),
      cheat: viewCheat, case: () => page(G.caseStudy), notes: viewNotes, settings: viewSettings, solutions: viewSolutions
    };
    view.innerHTML = (pages[r] || viewHome)();
    if (r === 'essay') afterEssayRender();
    if (r === 'templates') updateTemplateCounts();
    view.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function renderNav() {
    const r = route();
    $('#rail').innerHTML = NAV.map((grp) => `
      <div class="nav-group">
        <div class="nav-label">${grp.g}</div>
        ${grp.items.map(([k, label]) => `<a href="#${k}" class="nav-item${k === r ? ' on' : ''}"${k === r ? ' aria-current="page"' : ''}>${label}</a>`).join('')}
      </div>`).join('') + `<div class="nav-foot">자체 제작 연습 자료. 공식 기출이 아님.</div>`;
  }

  const page = (html) => `<article class="doc">${html}</article>`;

  // ---------------------------------------------------------------- 홈
  function viewHome() {
    const attempts = store.get('attempts', []);
    const todo = [
      ['t1', '시험 정보 읽기 (5분)', 'info'],
      ['t2', '객관식 가이드 → 지식평가 모의 A', 'guide-mc'],
      ['t3', 'AI 과제형 가이드 → 활용평가 과제 1개', 'guide-task'],
      ['t4', '공식 체험판 3종 직접 풀기', 'info'],
      ['t5', '지식평가 모의 B + 검증 드릴', 'mock-knowledge'],
      ['t6', '활용평가 전체 90분 (과제 3은 토큰 분할 연습)', 'mock-task'],
      ['t6b', '틀린 과제는 정답·풀이 가이드의 회차별 프롬프트와 비교', 'solutions'],
      ['t7', '오답노트, 치트시트 함정 열 훑기', 'notes'],
      ['t8', '당일 체크리스트', 'checklist']
    ];
    const done = store.get('todo', {});
    const last = attempts.slice(-5).reverse();
    return `
<section class="hero">
  <p class="eyebrow">SK하이닉스 AI 해커톤 2026 · 1차 예선</p>
  <h1>프로그래머스 AI 역량평가<br>실전 대비 노트</h1>
  <p class="lede">1차 예선은 10/17(토)~18(일) 중 하루, 온라인. 세션은 20문항 30분과 16문항 90분으로 알려져 있다(영상 기준). 아래 숫자가 시험장의 실제 단위다.</p>
  <div class="gauge-row">
    <div class="gauge"><span class="g-num">1,000<small>자</small></span><span class="g-lab">프롬프트 입력 한도</span></div>
    <div class="gauge"><span class="g-num">20,000<small>토큰</small></span><span class="g-lab">질문 1회 첨부 한도</span></div>
    <div class="gauge"><span class="g-num">10<small>회</small></span><span class="g-lab">1~4번 공유 (체험판)</span></div>
    <div class="gauge"><span class="g-num">90<small>초</small></span><span class="g-lab">지식평가 문항당</span></div>
    <div class="gauge"><span class="g-num">22<small>분</small></span><span class="g-lab">과제 1개당</span></div>
  </div>
  <div class="cta-row">
    <button class="btn primary" data-act="start-k" data-set="A">지식평가 모의 A · 20문항 30분</button>
    <button class="btn" data-act="start-t" data-tasks="T1" data-min="22">과제 1개 · 22분</button>
    <button class="btn" data-act="start-t" data-tasks="T1,T2,T3,T4" data-min="90">활용평가 전체 · 90분</button>
  </div>
</section>

<section class="home-grid">
  <div class="panel">
    <h2>준비 순서</h2>
    <ol class="todo">
      ${todo.map(([k, label, to]) => `<li><label><input type="checkbox" id="todo-${k}" data-act="todo" data-k="${k}"${done[k] ? ' checked' : ''}> <span>${label}</span></label> <a href="#${to}">열기</a></li>`).join('')}
    </ol>
  </div>
  <div class="panel">
    <h2>최근 기록</h2>
    ${last.length ? `<div class="table-wrap"><table class="compact"><thead><tr><th>날짜</th><th>종류</th><th>점수</th></tr></thead><tbody>
      ${last.map((a) => `<tr><td class="num">${esc(a.date)}</td><td>${esc(a.label)}</td><td class="num">${a.score}/${a.total}</td></tr>`).join('')}
    </tbody></table></div>` : '<p class="muted">아직 기록이 없다. 모의고사를 한 번 풀면 여기에 쌓인다.</p>'}
    <p class="muted small">기록은 이 브라우저에만 저장된다.</p>
  </div>
</section>

<section class="panel">
  <h2>핵심 전략 다섯 줄</h2>
  <ol class="steps tight">
    <li><b>지식평가</b>: 질문 문장 → 보기 차이 → 지문 조건 순서로 읽는다. 단정 표현은 지운다.</li>
    <li><b>과제형</b>: 4문항을 먼저 다 읽고, ‘문제’ 버튼으로 1~4번을 모두 넣어 첫 질문에 한꺼번에 판정을 받는다.</li>
    <li><b>첨부</b>: 파일 목록 토큰 합을 보고 20,000을 넘으면 기준 문서 → 묶음 처리 → 취합으로 나눈다.</li>
    <li><b>검증</b>: AI 계산은 식으로 받고 내가 다시 계산한다. 목록은 개수부터 맞춘다.</li>
    <li><b>보안</b>: 실명·연락처 같은 민감정보는 프롬프트에 다시 쓰지 않는다.</li>
  </ol>
</section>`;
  }

  // ---------------------------------------------------------------- 체크리스트
  function viewChecklist() {
    const c = G.checklist || { before: [], during: [] };
    const done = store.get('check', {});
    const list = (arr, p) => `<ul class="checks interactive">${arr.map((t, i) => `<li><label><input type="checkbox" id="chk-${p}${i}" data-act="check" data-k="${p}${i}"${done[p + i] ? ' checked' : ''}> <span>${esc(t)}</span></label></li>`).join('')}</ul>`;
    return page(`<h1>전날·당일 체크리스트</h1>
      <p class="lede">체크 상태는 이 브라우저에 저장된다.</p>
      <h2>전날까지</h2>${list(c.before, 'b')}
      <h2>시험 중</h2>${list(c.during, 'd')}`);
  }

  // ---------------------------------------------------------------- 템플릿
  function viewTemplates() {
    const s = S();
    return page(`<h1>프롬프트 템플릿</h1>
      <p class="lede">시험장에서는 복사가 안 되니 구조를 외우는 용도다. 글자 수는 입력창 한도(${fmt(s.charCap)}자) 기준으로 센다. 대괄호 부분만 과제에 맞게 바꿔 쓴다.</p>
      ${(G.templates || []).map((t, i) => `
        <section class="tmpl-card">
          <div class="tmpl-head"><h2>${esc(t.name)}</h2><span class="count" data-count-for="tmpl-${i}"></span></div>
          <p class="muted">${esc(t.when)}</p>
          <textarea id="tmpl-${i}" class="tmpl-edit" rows="6" data-counter="tmpl-${i}">${esc(t.text)}</textarea>
          <div class="row"><button class="btn small" data-act="copy-el" data-target="tmpl-${i}">복사 (연습용)</button></div>
        </section>`).join('')}
      <section class="tmpl-card">
        <div class="tmpl-head"><h2>글자 수 재기</h2><span class="count" data-count-for="tmpl-free"></span></div>
        <p class="muted">직접 쓴 프롬프트를 붙여 넣어 ${fmt(s.charCap)}자 안에 드는지 본다.</p>
        <textarea id="tmpl-free" class="tmpl-edit" rows="5" data-counter="tmpl-free" placeholder="여기에 프롬프트를 쓰거나 붙여 넣기"></textarea>
      </section>`);
  }
  function updateTemplateCounts() {
    const cap = S().charCap;
    $$('[data-counter]').forEach((ta) => {
      const out = $(`[data-count-for="${ta.dataset.counter}"]`);
      if (out) { const n = ta.value.length; out.textContent = `${fmt(n)}/${fmt(cap)}자`; out.classList.toggle('over', n > cap); }
    });
  }

  // ---------------------------------------------------------------- 치트시트
  function viewCheat() {
    const rows = G.cheat || [];
    return page(`<h1>개념 치트시트</h1>
      <p class="lede">세 번째 열은 시험 보기에서 오답으로 자주 쓰이는 문장이다. 시험 직전에는 그 열만 훑어도 된다.</p>
      <label class="field inline"><span>찾기</span><input id="cheat-q" type="search" placeholder="예: RAG, 가명" data-act="cheat-filter"></label>
      <div class="table-wrap"><table class="cheat"><thead><tr><th>개념</th><th>한 줄 정리</th><th>오답 보기에 자주 나오는 말</th></tr></thead>
      <tbody>${rows.map((r) => `<tr><td><b>${esc(r[0])}</b></td><td>${esc(r[1])}</td><td class="trap">${esc(r[2])}</td></tr>`).join('')}</tbody></table></div>`);
  }

  // ---------------------------------------------------------------- 지식평가 메뉴
  function viewKMenu() {
    const sets = window.KNOWLEDGE_SETS || {};
    const shorts = K.filter((q) => q.type === 'short').length;
    const ox = K.filter((q) => q.type === 'ox').length;
    return page(`<h1>지식평가 모의고사</h1>
      <p class="lede">세션 1(20문항 30분 추정)을 그대로 재현한다. 문항 ${K.length}개 (4지선다 ${K.length - shorts - ox}, O/X ${ox}, 단답형 ${shorts}). 모두 자체 제작이며, 공식 체험판의 형식과 출제 범위를 참고했다.</p>
      <div class="menu-grid">
        <button class="menu-card" data-act="start-k" data-set="A"><b>세트 A</b><span>20문항 · 30분</span></button>
        <button class="menu-card" data-act="start-k" data-set="B"><b>세트 B</b><span>20문항 · 30분</span></button>
        <button class="menu-card" data-act="start-k" data-set="R"><b>무작위 20</b><span>전체 문제은행에서 · 30분</span></button>
        <button class="menu-card" data-act="start-k" data-set="S"><b>단답형만</b><span>${shorts}문항 · 문항당 90초</span></button>
        <button class="menu-card" data-act="start-k" data-set="ALL"><b>전체 풀기</b><span>${K.length}문항 · 문항당 90초</span></button>
      </div>
      <p class="muted small">보기 순서는 매번 섞인다. 시험 시간 없이 풀려면 설정에서 ‘시간 제한 없이 연습’을 켠다.</p>`);
  }

  function startKnowledge(set, ids) {
    let list;
    const sets = window.KNOWLEDGE_SETS || {};
    let label;
    if (ids) { list = ids; label = '오답 다시 풀기'; }
    else if (set === 'A' || set === 'B') { list = sets[set]; label = `지식평가 세트 ${set}`; }
    else if (set === 'R') { list = shuffle(K.map((q) => q.id)).slice(0, 20); label = '지식평가 무작위 20'; }
    else if (set === 'S') { list = K.filter((q) => q.type === 'short').map((q) => q.id); label = '단답형 모음'; }
    else { list = K.map((q) => q.id); label = '지식평가 전체'; }
    list = list.filter((id) => KMAP[id]);
    const perm = {};
    list.forEach((id) => { const q = KMAP[id]; if (q.type === 'mc') perm[id] = shuffle(q.options.map((_, i) => i)); });
    const dur = (set === 'A' || set === 'B' || set === 'R') ? 30 * 60 * 1000 : list.length * 90 * 1000;
    state.exam = { kind: 'knowledge', label, list, perm, idx: 0, answers: {}, flags: {}, start: Date.now(), duration: dur };
    state.result = null;
    render();
  }

  function qTypeLabel(q) { return q.type === 'mc' ? '객관식' : q.type === 'ox' ? 'O/X' : '주관식'; }

  function viewKExam() {
    const ex = state.exam;
    const id = ex.list[ex.idx];
    const q = KMAP[id];
    const answered = ex.list.filter((x) => ex.answers[x] != null && ex.answers[x] !== '').length;
    let body = '';
    if (q.type === 'mc') {
      body = `<div class="opts" role="radiogroup" aria-label="보기">${ex.perm[id].map((oi, k) => `
        <label class="opt${ex.answers[id] === oi ? ' on' : ''}"><input type="radio" name="opt" id="opt-${k}" value="${oi}" data-act="k-pick" data-v="${oi}"${ex.answers[id] === oi ? ' checked' : ''}>
        <span class="opt-n">${k + 1}</span><span class="opt-t">${esc(q.options[oi])}</span></label>`).join('')}</div>`;
    } else if (q.type === 'ox') {
      body = `<p class="muted small">다음 설명이 참이면 O, 거짓이면 X를 고르세요.</p><div class="opts ox" role="radiogroup" aria-label="O 또는 X">${['O', 'X'].map((v, k) => `
        <label class="opt${ex.answers[id] === v ? ' on' : ''}"><input type="radio" name="opt" id="opt-${k}" value="${v}" data-act="k-pick" data-v="${v}"${ex.answers[id] === v ? ' checked' : ''}>
        <span class="opt-n">${k + 1}</span><span class="opt-t big">${v}</span></label>`).join('')}</div>`;
    } else {
      body = `<label class="field"><span>답안 입력</span><input id="k-short" type="text" autocomplete="off" value="${esc(ex.answers[id] || '')}" data-act="k-short" placeholder="답을 입력하세요"></label>`;
    }
    return `
<div class="exam">
  <div class="exam-bar">
    <div class="exam-title"><b>${esc(ex.label)}</b><span class="muted"> · 문항당 90초</span></div>
    <div class="timer" id="timer" aria-live="off">--:--</div>
    <div class="exam-actions"><button class="btn ghost small" data-act="quit">그만두기</button><button class="btn primary small" data-act="submit-ask">채점 후 종료하기</button></div>
  </div>
  <div class="kgrid">
    <nav class="qnav" aria-label="문항 목록">
      <div class="qnav-label">객관식/주관식</div>
      <div class="qnav-grid">${ex.list.map((x, i) => {
        const a = ex.answers[x] != null && ex.answers[x] !== '';
        return `<button class="qn${i === ex.idx ? ' cur' : ''}${a ? ' done' : ''}${ex.flags[x] ? ' flag' : ''}" data-act="k-go" data-i="${i}" aria-label="${i + 1}번${a ? ' 답함' : ''}${ex.flags[x] ? ' 다시 풀 문제' : ''}">${i + 1}</button>`;
      }).join('')}</div>
      <div class="legend"><span class="lg done"></span>답함 <span class="lg flag"></span>다시 풀 문제</div>
    </nav>
    <section class="qpane">
      <div class="q-head"><span class="q-num">${ex.idx + 1}. ${qTypeLabel(q)}</span><span class="q-area">${esc(q.area)}</span>
        <button class="flag-btn${ex.flags[id] ? ' on' : ''}" data-act="k-flag" aria-pressed="${ex.flags[id] ? 'true' : 'false'}">다시 풀 문제</button></div>
      <p class="q-stem${S().copyLock ? ' nocopy' : ''}">${esc(q.stem)}</p>
      ${body}
    </section>
  </div>
  <div class="exam-foot">
    <span class="muted">객/주관식 ${ex.list.length}문제 중 <b>${answered}</b>문제 답함</span>
    <span class="pace" id="pace"></span>
    <div class="row"><button class="btn small" data-act="k-prev"${ex.idx === 0 ? ' disabled' : ''}>이전 문제</button><button class="btn small" data-act="k-next"${ex.idx === ex.list.length - 1 ? ' disabled' : ''}>다음 문제</button></div>
  </div>
  ${confirmBox()}
</div>`;
  }

  function gradeK(q, v) {
    if (v == null || v === '') return false;
    if (q.type === 'mc') return v === q.answer;
    if (q.type === 'ox') return v === q.answer;
    const norm = (s) => String(s).toLowerCase().replace(/[\s\-_.()%]/g, '');
    if (q.numeric != null) { const n = parseNum(v); return n != null && Math.abs(n - q.numeric) < 1e-9; }
    return q.answer.some((a) => norm(a) === norm(v));
  }

  function finishKnowledge(auto) {
    const ex = state.exam;
    const items = ex.list.map((id) => { const q = KMAP[id]; const v = ex.answers[id]; return { id, q, v, ok: gradeK(q, v) }; });
    const score = items.filter((x) => x.ok).length;
    const used = Date.now() - ex.start;
    const wrong = items.filter((x) => !x.ok).map((x) => x.id);
    const notes = store.get('wrongK', {});
    wrong.forEach((id) => { notes[id] = (notes[id] || 0) + 1; });
    store.set('wrongK', notes);
    pushAttempt({ label: ex.label, score, total: items.length });
    state.result = { kind: 'knowledge', label: ex.label, items, score, used, auto, perm: ex.perm };
    state.exam = null;
    render();
  }

  function viewKResult() {
    const r = state.result;
    const byArea = {};
    r.items.forEach((x) => { const a = x.q.area.split('·')[0]; byArea[a] = byArea[a] || { n: 0, ok: 0 }; byArea[a].n++; if (x.ok) byArea[a].ok++; });
    const ansText = (q, v) => {
      if (v == null || v === '') return '(무응답)';
      if (q.type === 'mc') return q.options[v];
      return String(v);
    };
    const correctText = (q) => q.type === 'mc' ? q.options[q.answer] : q.type === 'ox' ? q.answer : q.answer[0];
    return `
<article class="doc wide">
  <p class="eyebrow">채점 결과${r.auto ? ' · 시간 종료로 자동 제출' : ''}</p>
  <h1>${esc(r.label)}: ${r.score} / ${r.items.length}</h1>
  <p class="lede">걸린 시간 ${mmss(r.used)}. 틀린 문항은 오답노트에 저장했다.</p>
  <div class="row"><button class="btn primary" data-act="result-close">목록으로</button>
  ${r.items.some((x) => !x.ok) ? `<button class="btn" data-act="retry-wrong-k">틀린 것만 다시</button>` : ''}<button class="btn" data-act="go-sol" data-tab="knowledge">보기별 해설 전체 보기</button></div>
  <h2>영역별</h2>
  <div class="area-bars">${Object.entries(byArea).map(([a, v]) => `<div class="area"><span class="a-name">${esc(a)}</span><span class="a-bar"><i style="width:${Math.round(v.ok / v.n * 100)}%"></i></span><span class="a-num num">${v.ok}/${v.n}</span></div>`).join('')}</div>
  <h2>문항별 해설</h2>
  ${r.items.map((x, i) => `
  <details class="review ${x.ok ? 'ok' : 'bad'}"${x.ok ? '' : ' open'}>
    <summary><span class="badge ${x.ok ? 'ok' : 'bad'}">${x.ok ? '정답' : '오답'}</span> <b>${i + 1}.</b> ${esc(x.q.area)} <span class="muted">· ${qTypeLabel(x.q)}</span></summary>
    <div class="ans-grid"><div><span class="muted small">내 답</span><p>${esc(ansText(x.q, x.v))}</p></div><div><span class="muted small">정답</span><p><b>${esc(correctText(x.q))}</b></p></div></div>
    ${kExplain(x.q, x.v)}
  </details>`).join('')}
</article>`;
  }

  function srcList(src) {
    if (!src || !src.length) return '';
    return `<p class="src">근거: ${src.map((s) => `<a href="${esc(s.u)}" target="_blank" rel="noopener">${esc(s.t)}</a>`).join(' · ')}</p>`;
  }

  function pushAttempt(a) {
    const list = store.get('attempts', []);
    const d = new Date();
    list.push(Object.assign({ date: `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}` }, a));
    store.set('attempts', list.slice(-60));
  }

  // ---------------------------------------------------------------- 활용평가 메뉴
  function viewTMenu() {
    return page(`<h1>활용평가 모의고사</h1>
      <p class="lede">세션 2(16문항 90분 추정)를 재현한다. 과제 4개 × 4문항. 화면은 프로그래머스 체험판처럼 지문·파일 목록·문항, 오른쪽 AI 어시스트로 구성했다. AI 어시스트 제약(1,000자, 첨부 20,000토큰, 10회, 쿨타임)을 그대로 건다.</p>
      <div class="menu-grid">
        <button class="menu-card wide" data-act="start-t" data-tasks="T1,T2,T3,T4" data-min="90"><b>전체 세션</b><span>과제 4개 · 16문항 · 90분</span></button>
        ${TASKS.map((t, i) => `<button class="menu-card" data-act="start-t" data-tasks="${t.id}" data-min="22"><b>과제 ${i + 1}. ${esc(t.title)}</b><span>4문항 · 22분 · 파일 ${t.files.length}개 · 약 ${fmt(t.totalTokens)}토큰</span></button>`).join('')}
      </div>
      <h2>AI 어시스트 연결</h2>
      <p>${aiModeText()}</p>
      <p class="muted small">모든 정답은 생성 스크립트(tools/gen_tasks.py)가 규칙대로 계산했고, 별도 검산 스크립트(tools/verify_tasks.py)로 다시 확인했다.</p>`);
  }

  function aiModeText() {
    const s = S();
    if (s.provider === 'none' || !s.apiKey) return '지금은 <b>프롬프트 연습 모드</b>다. 보낸 프롬프트를 점검해 주고, 응답이 필요하면 ‘외부 AI용 복사’로 ChatGPT나 Claude에 붙여 넣어 연습한다. 진짜 AI 응답을 받으려면 <a href="#settings">설정</a>에서 본인 API 키를 연결한다.';
    return `<b>${esc({ openai: 'OpenAI', anthropic: 'Anthropic', gemini: 'Google Gemini' }[s.provider])} · ${esc(s.model || '모델 미입력')}</b>로 연결되어 있다. 키는 이 브라우저에만 저장된다. 실제 시험의 모델과 다를 수 있다.`;
  }

  function startTask(ids, minutes) {
    const s = S();
    const tasks = ids.filter((id) => TMAP[id]);
    const ai = {};
    tasks.forEach((id) => { ai[id] = { left: s.turns, msgs: [], attach: [], sel: [], cool: 0, draft: '', busy: false }; });
    const firstFile = {};
    tasks.forEach((id) => { firstFile[id] = TMAP[id].files[0].name; });
    state.exam = {
      kind: 'task', label: tasks.length > 1 ? '활용평가 전체 세션' : `활용평가 · ${TMAP[tasks[0]].title}`,
      tasks, cur: 0, answers: {}, flags: {}, ai, view: firstFile, taskTime: {}, lastTick: Date.now(),
      start: Date.now(), duration: minutes * 60 * 1000, menu: null, err: ''
    };
    state.result = null;
    render();
  }

  const curTask = () => TMAP[state.exam.tasks[state.exam.cur]];

  function viewTExam() {
    const ex = state.exam;
    const t = curTask();
    const s = S();
    const allQ = ex.tasks.flatMap((id) => TMAP[id].questions.map((q) => ({ q, tid: id })));
    const answered = allQ.filter(({ q }) => ex.answers[q.id] != null && ex.answers[q.id] !== '').length;
    const lock = s.copyLock ? ' nocopy' : '';
    const vf = ex.view[t.id];
    const file = t.files.find((f) => f.name === vf) || t.files[0];
    const ai = ex.ai[t.id];
    const qBase = ex.tasks.indexOf(t.id) * 4;
    return `
<div class="exam task">
  <div class="exam-bar">
    <div class="exam-title"><b>${esc(ex.label)}</b></div>
    ${ex.tasks.length > 1 ? `<div class="task-tabs" role="tablist">${ex.tasks.map((id, i) => {
      const n = TMAP[id].questions.filter((q) => ex.answers[q.id] != null && ex.answers[q.id] !== '').length;
      return `<button role="tab" class="ttab${i === ex.cur ? ' on' : ''}" aria-selected="${i === ex.cur}" data-act="t-go" data-i="${i}">과제 ${i + 1} <span class="num">${n}/4</span></button>`;
    }).join('')}</div>` : ''}
    <div class="timer" id="timer">--:--</div>
    <div class="exam-actions"><button class="btn ghost small" data-act="quit">그만두기</button><button class="btn primary small" data-act="submit-ask">채점 후 종료하기</button></div>
  </div>
  <div class="tgrid">
    <nav class="qnav" aria-label="문항 목록">
      <div class="qnav-label">객관식/주관식</div>
      ${ex.tasks.map((id, ti) => `<div class="qnav-task${ti === ex.cur ? ' cur' : ''}"><span class="muted small">과제 ${TASKS.findIndex((x) => x.id === id) + 1}</span><div class="qnav-grid">${TMAP[id].questions.map((q, qi) => {
        const a = ex.answers[q.id] != null && ex.answers[q.id] !== '';
        return `<button class="qn${a ? ' done' : ''}${ex.flags[q.id] ? ' flag' : ''}" data-act="t-jump" data-ti="${ti}" data-q="${q.id}">${ti * 4 + qi + 1}</button>`;
      }).join('')}</div></div>`).join('')}
      <div class="task-clock" id="taskclock"></div>
    </nav>
    <section class="passage" id="passage">
      <div class="p-head"><span class="q-num">${qBase + 1} ~ ${qBase + 4}</span><span class="muted">다음을 읽고 문제를 풀어주세요.</span><span class="ai-left-mini">AI 어시스트 남은 횟수 <b>${ai.left} / ${s.turns}회</b></span></div>
      <h2 class="t-title">${esc(t.title)}</h2>
      <p class="${lock}">${esc(t.scenario)}</p>
      <h3>주의사항</h3>
      <ul class="${lock}">${t.cautions.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>
      <h3>파일 목록</h3>
      <div class="table-wrap filelist"><table class="compact"><thead><tr><th>파일명</th><th class="num">토큰량</th><th></th></tr></thead><tbody>
        ${t.files.map((f) => {
          const on = ai.attach.includes(f.name);
          return `<tr class="${f.name === file.name ? 'sel' : ''}"><td><button class="linkish" data-act="t-view" data-f="${esc(f.name)}">${esc(f.name)}</button></td><td class="num">${fmt(f.tokens)}</td>
          <td class="right"><button class="btn tiny${on ? ' on' : ''}" data-act="t-attach" data-f="${esc(f.name)}" aria-pressed="${on}">${on ? '첨부됨' : 'AI 질문에 추가'}</button></td></tr>`;
        }).join('')}
        <tr class="sum"><td>합계</td><td class="num">${fmt(t.totalTokens)}</td><td class="right muted small">${t.totalTokens > s.attachCap ? `한 번에 첨부 불가 (한도 ${fmt(s.attachCap)})` : '한 번에 첨부 가능'}</td></tr>
      </tbody></table></div>
      ${ex.err ? `<p class="err" role="alert">${esc(ex.err)}</p>` : ''}
      <div class="viewer">
        <div class="viewer-head"><b>${esc(file.name)}</b><span class="num muted">${fmt(file.tokens)} 토큰</span>
          <button class="btn tiny${ai.attach.includes(file.name) ? ' on' : ''}" data-act="t-attach" data-f="${esc(file.name)}">${ai.attach.includes(file.name) ? '첨부됨' : 'AI 질문에 추가'}</button></div>
        <div class="viewer-body${lock}">${renderFile(file)}</div>
      </div>
      <div class="qlist">
        ${t.questions.map((q, qi) => taskQuestion(q, qBase + qi + 1)).join('')}
      </div>
    </section>
    <section class="assist" aria-label="AI 어시스트">${viewAssist(t, ai, qBase)}</section>
  </div>
  <div class="exam-foot">
    <span class="muted">객/주관식 ${allQ.length}문제 중 <b>${answered}</b>문제 답함</span>
    <span class="pace" id="pace"></span>
    <div class="row">${ex.tasks.length > 1 ? `<button class="btn small" data-act="t-prev"${ex.cur === 0 ? ' disabled' : ''}>이전 과제</button><button class="btn small" data-act="t-next"${ex.cur === ex.tasks.length - 1 ? ' disabled' : ''}>다음 과제</button>` : ''}</div>
  </div>
  ${confirmBox()}
</div>`;
  }

  function renderFile(f) {
    if (f.kind === 'csv') {
      const lines = f.text.trim().split('\n');
      const rows = lines.map((l) => l.split(','));
      return `<div class="csv-wrap"><table class="csv"><thead><tr><th class="rn">#</th>${rows[0].map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1).map((r, i) => `<tr><td class="rn">${i + 1}</td>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    }
    return `<pre class="doc-pre">${esc(f.text)}</pre>`;
  }

  function taskQuestion(q, n) {
    const ex = state.exam;
    const v = ex.answers[q.id];
    let input;
    if (q.type === 'mc') {
      input = `<div class="opts">${q.options.map((o, i) => `<label class="opt${v === i ? ' on' : ''}"><input type="radio" name="${q.id}" id="${q.id}-${i}" data-act="t-pick" data-q="${q.id}" data-v="${i}"${v === i ? ' checked' : ''}><span class="opt-n">${i + 1}</span><span class="opt-t">${esc(o)}</span></label>`).join('')}</div>`;
    } else {
      input = `<label class="field"><span>답안 입력${q.unit ? ` (단위: ${esc(q.unit)})` : ''}</span><input type="text" id="ans-${q.id}" autocomplete="off" data-act="t-short" data-q="${q.id}" value="${esc(v || '')}" placeholder="답을 입력하세요"></label>`;
    }
    return `<div class="tq" id="q-${q.id}">
      <div class="q-head"><span class="q-num">${n}. ${q.type === 'mc' ? '객관식' : '주관식'}</span>
      <button class="flag-btn${ex.flags[q.id] ? ' on' : ''}" data-act="t-flag" data-q="${q.id}" aria-pressed="${ex.flags[q.id] ? 'true' : 'false'}">다시 풀 문제</button>
      <button class="linkish small" data-act="to-top">지문으로 이동</button></div>
      <p class="q-stem">${esc(q.prompt)}</p>${input}</div>`;
  }

  function viewAssist(t, ai, qBase) {
    const s = S();
    const attTok = ai.attach.reduce((a, n) => a + (t.files.find((f) => f.name === n) || { tokens: 0 }).tokens, 0);
    const menu = state.exam.menu;
    const mode = s.provider !== 'none' && s.apiKey ? 'live' : 'practice';
    return `
<div class="ai-head"><b>AI 어시스트</b><span class="ai-left${ai.left <= 2 ? ' low' : ''}">${ai.left}회 남음</span></div>
<p class="ai-mode ${mode}">${mode === 'live' ? `연결됨: ${esc(s.model || '모델 미입력')}` : '연습 모드: 응답 대신 프롬프트 점검'}</p>
<div class="ai-log" id="ailog" aria-live="polite">
  ${ai.msgs.length ? '' : `<p class="ai-empty">${qBase + 1}-${qBase + 4}번 문제에 대해 질문해보세요.<br><span class="small">‘문제’로 문항을 고르고, 파일 목록에서 ‘AI 질문에 추가’로 자료를 붙인다.</span></p>`}
  ${ai.msgs.map((m, i) => msgBubble(m, i)).join('')}
  ${ai.busy ? '<div class="bubble ai"><span class="dots" aria-label="응답 생성 중">응답 생성 중</span></div>' : ''}
</div>
<div class="ai-compose">
  <div class="chips">
    <div class="pop-wrap">
      <button class="chip" data-act="menu" data-m="q" aria-expanded="${menu === 'q'}">문제 <b>${ai.sel.length}</b></button>
      ${menu === 'q' ? `<div class="pop" role="menu">${t.questions.map((q, i) => `<label class="pop-item"><input type="checkbox" id="sel-${q.id}" data-act="sel-q" data-q="${q.id}"${ai.sel.includes(q.id) ? ' checked' : ''}> ${qBase + i + 1}. ${q.type === 'mc' ? '객관식' : '주관식'}</label>`).join('')}
        <div class="pop-foot"><button class="linkish small" data-act="sel-all">전체 선택</button><button class="linkish small" data-act="menu" data-m="">닫기</button></div></div>` : ''}
    </div>
    <div class="pop-wrap">
      <button class="chip" data-act="menu" data-m="a" aria-expanded="${menu === 'a'}">첨부 파일 <b>${ai.attach.length}</b></button>
      ${menu === 'a' ? `<div class="pop wide" role="menu"><div class="pop-title"><b>첨부 파일</b><span class="num ${attTok > s.attachCap ? 'over' : ''}">${fmt(attTok)}/${fmt(s.attachCap)} 토큰</span><button class="linkish small" data-act="att-clear">전체 삭제</button></div>
        ${ai.attach.length ? ai.attach.map((n) => `<div class="pop-item"><span>${esc(n)}</span><span class="num muted">${fmt((t.files.find((f) => f.name === n) || {}).tokens || 0)}</span><button class="linkish small" data-act="t-attach" data-f="${esc(n)}">빼기</button></div>`).join('') : '<p class="muted small">파일 목록에서 추가한 파일이 여기에 표시됩니다.</p>'}
        <div class="pop-foot"><button class="linkish small" data-act="menu" data-m="">닫기</button></div></div>` : ''}
    </div>
    <span class="tok num${attTok > s.attachCap ? ' over' : ''}">${fmt(attTok)}/${fmt(s.attachCap)}</span>
  </div>
  <label class="sr-only" for="aiinput">AI에게 보낼 질문</label>
  <textarea id="aiinput" rows="5" placeholder="무엇을 도와드릴까요?" data-act="ai-input">${esc(ai.draft)}</textarea>
  <div class="compose-foot"><span class="count num" id="aicount">${fmt(ai.draft.length)}/${fmt(s.charCap)}</span>
  <button class="btn primary small" id="aisend" data-act="ai-send"${ai.left <= 0 || ai.busy ? ' disabled' : ''}>보내기</button></div>
</div>`;
  }

  function msgBubble(m, i) {
    if (m.role === 'user') {
      return `<div class="bubble me"><div class="meta">${m.sel.length ? `문제 ${m.sel.map(esc).join(', ')}` : '문제 선택 없음'} · 첨부 ${m.files.length}개 (${fmt(m.tokens)}토큰) · ${fmt(m.text.length)}자</div>
        <div class="b-text">${esc(m.text)}</div>
        <div class="checks-row">${m.checks.map((c) => `<span class="ck ${c.ok ? 'ok' : 'no'}">${c.ok ? '✓' : '·'} ${esc(c.k)}</span>`).join('')}</div></div>`;
    }
    if (m.role === 'ai') return `<div class="bubble ai"><div class="b-text">${esc(m.text)}</div></div>`;
    return `<div class="bubble sys"><div class="b-text">${m.html}</div>${m.copy != null ? `<button class="btn tiny" data-act="copy-msg" data-i="${i}">외부 AI용 복사</button>` : ''}</div>`;
  }

  function promptChecks(text, selN, fileN, essay) {
    const t = text;
    const list = [
      { k: '문항 지정', ok: selN > 0 || /([1-4]\s*[~\-–]\s*[1-4]|[1-4]번|문항|Q[1-4])/.test(t) },
      { k: '자료 지정', ok: fileN > 0 || /(\.csv|\.md|\.pdf|\.txt|첨부|파일)/.test(t) },
      { k: '규칙·조건', ok: /(규칙|기준|규정|조건|제외|이상|이하|초과|미만|포함|판정표)/.test(t) },
      { k: '처리 순서', ok: /(순서|①|1\)|1\.|먼저|단계|→)/.test(t) },
      { k: '출력 형식', ok: /(표|형식|목록|오름차순|내림차순|쉼표|소수점|단위|줄)/.test(t) },
      { k: '근거·계산식', ok: /(근거|인용|계산식|중간값|행|ID|id|출처|검산|교차)/.test(t) },
      { k: '불확실 처리', ok: /(확인 필요|모르면|추측|지어내|만들지 마|생략|애매|불확실)/.test(t) }
    ];
    if (essay) list.push({ k: '비식별', ok: /(비식별|익명|가명|담당자 A|마스킹|실명)/.test(t) });
    return list;
  }

  function buildContext(t, ai, prompt, selIds, files) {
    const parts = [];
    if (selIds.length) {
      parts.push('[선택한 문제]');
      selIds.forEach((qid) => {
        const qi = t.questions.findIndex((q) => q.id === qid);
        const q = t.questions[qi];
        parts.push(`${qi + 1}. ${q.prompt}` + (q.type === 'mc' ? '\n' + q.options.map((o, i) => `  ${i + 1}) ${o}`).join('\n') : ''));
      });
      parts.push('[지문]\n' + t.scenario + '\n주의사항: ' + t.cautions.join(' / '));
    }
    files.forEach((n) => { const f = t.files.find((x) => x.name === n); if (f) parts.push(`[첨부 파일: ${f.name}]\n${f.text}`); });
    parts.push('[질문]\n' + prompt);
    return parts.join('\n\n');
  }

  async function sendAI(ctxObj, ai, opts) {
    const s = S();
    const prompt = ai.draft.trim();
    if (!prompt) { toast('질문을 입력하세요.'); return; }
    if (prompt.length > s.charCap) { toast(`입력창은 ${fmt(s.charCap)}자까지다. 지금 ${fmt(prompt.length)}자.`); return; }
    if (ai.left <= 0) { toast('남은 횟수가 없다.'); return; }
    if (Date.now() < ai.cool) { toast('응답 대기 시간이 끝나야 보낼 수 있다.'); return; }
    const files = ai.attach.slice();
    const tokens = files.reduce((a, n) => a + ((ctxObj.files.find((f) => f.name === n) || {}).tokens || 0), 0);
    if (tokens > s.attachCap) { toast(`첨부 합계 ${fmt(tokens)}토큰이 한도 ${fmt(s.attachCap)}를 넘는다.`); return; }
    const sel = (ai.sel || []).slice();
    const selLabels = sel.map((qid) => String(ctxObj.questions ? ctxObj.questions.findIndex((q) => q.id === qid) + 1 + (opts.qBase || 0) : qid));
    const full = buildContext(ctxObj, ai, prompt, sel, files);
    ai.msgs.push({ role: 'user', text: prompt, sel: selLabels, files, tokens, checks: promptChecks(prompt, sel.length, files.length, opts.essay), full });
    ai.left -= 1;
    ai.cool = Date.now() + s.cooldown * 1000;
    ai.draft = '';
    if (s.clearAttach) ai.attach = [];
    const live = s.provider !== 'none' && s.apiKey;
    if (!live) {
      const missed = ai.msgs[ai.msgs.length - 1].checks.filter((c) => !c.ok).map((c) => c.k);
      ai.msgs.push({
        role: 'sys', copy: full,
        html: `연습 모드라 응답을 만들지 않았다. ${missed.length ? `이번 프롬프트에 빠진 요소: <b>${missed.map(esc).join(', ')}</b>.` : '점검 항목을 모두 갖췄다.'} 응답이 필요하면 아래 버튼으로 문항·첨부·질문을 한 번에 복사해 ChatGPT나 Claude에 붙여 넣는다. 실제 시험에서는 외부 AI를 쓸 수 없다.`
      });
      opts.rerender();
      return;
    }
    ai.busy = true; opts.rerender();
    try {
      const history = [];
      if (s.keepHistory) {
        for (let i = 0; i < ai.msgs.length - 1; i++) {
          const m = ai.msgs[i], n = ai.msgs[i + 1];
          if (m.role === 'user' && n && n.role === 'ai') {
            history.push({ role: 'user', content: m.text + (m.files.length ? `\n(이전 질문의 첨부 파일 ${m.files.length}개는 이번 질문에 포함되지 않음)` : '') });
            history.push({ role: 'ai', content: n.text });
          }
        }
      }
      history.push({ role: 'user', content: full });
      const sys = opts.essay
        ? '당신은 업무 보조 AI 어시스턴트입니다. 사용자가 첨부한 자료와 지시에 따라 한국어로 답합니다.'
        : '당신은 업무 보조 AI 어시스턴트입니다. 사용자가 고른 문제와 첨부한 자료를 바탕으로 한국어로 답합니다.';
      const out = await callAI(history, sys);
      ai.msgs.push({ role: 'ai', text: out || '(빈 응답)' });
    } catch (e) {
      ai.msgs.push({ role: 'sys', html: `AI 호출에 실패했다: ${esc(e.message || String(e))}. 키·모델 이름을 확인하거나, 이 페이지가 외부 호출을 막는 환경(예: claude.ai 미리보기)인지 확인한다. 횟수는 돌려준다.` });
      ai.left += 1;
      ai.cool = 0;
    } finally {
      ai.busy = false;
      opts.rerender();
    }
  }

  async function callAI(messages, system) {
    const s = S();
    if (!s.model) throw new Error('설정에서 모델 이름을 입력해야 한다');
    if (s.provider === 'openai') {
      const r = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + s.apiKey },
        body: JSON.stringify({ model: s.model, messages: [{ role: 'system', content: system }].concat(messages.map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content }))) })
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
      return j.choices && j.choices[0] && j.choices[0].message ? j.choices[0].message.content : '';
    }
    if (s.provider === 'anthropic') {
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-api-key': s.apiKey, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' },
        body: JSON.stringify({ model: s.model, max_tokens: 2048, system, messages: messages.map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content })) })
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
      return (j.content || []).map((c) => c.text || '').join('');
    }
    if (s.provider === 'gemini') {
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(s.model)}:generateContent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': s.apiKey },
        body: JSON.stringify({ systemInstruction: { parts: [{ text: system }] }, contents: messages.map((m) => ({ role: m.role === 'ai' ? 'model' : 'user', parts: [{ text: m.content }] })) })
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
      return ((j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts) || []).map((p) => p.text || '').join('');
    }
    throw new Error('연결된 AI가 없다');
  }

  function parseNum(v) {
    const s = String(v).replace(/[,\s원%건명석점]/g, '').replace(/^\+/, '');
    if (!/^-?\d+(\.\d+)?$/.test(s)) return null;
    return parseFloat(s);
  }

  function gradeT(q, v) {
    if (q.type === 'mc') return v === q.answer;
    if (v == null || String(v).trim() === '') return false;
    if (q.list) {
      const norm = (s) => String(s).toUpperCase().split(/[\s,，、;/]+/).map((x) => x.trim()).filter(Boolean);
      const a = norm(v), b = norm(q.answer);
      return q.ordered ? a.join(',') === b.join(',') : a.slice().sort().join(',') === b.slice().sort().join(',');
    }
    if (q.numeric) { const x = parseNum(v); return x != null && Math.abs(x - parseFloat(q.answer)) < 1e-9; }
    return String(v).trim() === String(q.answer).trim();
  }

  function finishTask(auto) {
    const ex = state.exam;
    const tasks = ex.tasks.map((id) => {
      const t = TMAP[id];
      return { t, items: t.questions.map((q) => ({ q, v: ex.answers[q.id], ok: gradeT(q, ex.answers[q.id]) })), ai: ex.ai[id], time: ex.taskTime[id] || 0 };
    });
    const all = tasks.flatMap((x) => x.items);
    const score = all.filter((x) => x.ok).length;
    const wrong = store.get('wrongT', {});
    all.filter((x) => !x.ok).forEach((x) => { wrong[x.q.id] = (wrong[x.q.id] || 0) + 1; });
    store.set('wrongT', wrong);
    pushAttempt({ label: ex.label, score, total: all.length });
    state.result = { kind: 'task', label: ex.label, tasks, score, total: all.length, used: Date.now() - ex.start, auto };
    state.exam = null;
    render();
  }

  function viewTResult() {
    const r = state.result;
    const s = S();
    const show = (q, v) => {
      if (v == null || v === '') return '(무응답)';
      return q.type === 'mc' ? q.options[v] : String(v);
    };
    return `
<article class="doc wide">
  <p class="eyebrow">채점 결과${r.auto ? ' · 시간 종료로 자동 제출' : ''}</p>
  <h1>${esc(r.label)}: ${r.score} / ${r.total}</h1>
  <p class="lede">걸린 시간 ${mmss(r.used)}. 과제마다 회차별 풀이(문제 선택, 첨부 파일, 프롬프트 전문, AI가 줘야 할 값)를 붙였다. 내 프롬프트 기록과 나란히 비교해 본다.</p>
  <div class="row"><button class="btn primary" data-act="result-close">목록으로</button><button class="btn" data-act="go-sol" data-tab="task" data-task="${r.tasks[0].t.id}">정답·풀이 가이드에서 보기</button></div>
  ${r.tasks.map((x, ti) => {
    const used = s.turns - x.ai.left;
    const userMsgs = x.ai.msgs.filter((m) => m.role === 'user');
    return `
  <section class="result-task">
    <h2>과제: ${esc(x.t.title)} <span class="muted">${x.items.filter((i) => i.ok).length}/4 · ${mmss(x.time)} 사용 · AI ${used}회 사용</span></h2>
    ${x.items.map((it, i) => `
    <details class="review ${it.ok ? 'ok' : 'bad'}"${it.ok ? '' : ' open'}>
      <summary><span class="badge ${it.ok ? 'ok' : 'bad'}">${it.ok ? '정답' : '오답'}</span> <b>${i + 1}.</b> ${esc(it.q.prompt)}</summary>
      <div class="ans-grid"><div><span class="muted small">내 답</span><p>${esc(show(it.q, it.v))}</p></div><div><span class="muted small">정답</span><p><b>${esc(it.q.type === 'mc' ? it.q.options[it.q.answer] : it.q.answer)}</b></p></div></div>
      <p>${esc(it.q.why)}</p>
      <p class="trap-line"><b>함정</b> ${esc(it.q.trap)}</p>
    </details>`).join('')}
    <details class="walk"${x.items.every((i) => i.ok) ? '' : ' open'}>
      <summary>회차별 풀이 가이드: 문제 선택 · 첨부 파일 · 프롬프트 전문 · AI가 줘야 할 값</summary>
      ${renderWalkTask(x.t)}
    </details>
    <div class="two-col">
      <div class="panel">
        <h3>이 과제에서 가져갈 것</h3>
        <ul class="small">${x.t.lessons.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>
      </div>
      <div class="panel">
        <h3>내 프롬프트 기록 (${userMsgs.length}개)</h3>
        ${userMsgs.length ? userMsgs.map((m, i) => `<div class="mylog"><p class="small muted">${i + 1}회차 · 문제 ${m.sel.length}개 · 첨부 ${m.files.length}개 · ${fmt(m.text.length)}자</p><pre class="tmpl small">${esc(m.text)}</pre>
          <div class="checks-row">${m.checks.map((c) => `<span class="ck ${c.ok ? 'ok' : 'no'}">${c.ok ? '✓' : '·'} ${esc(c.k)}</span>`).join('')}</div></div>`).join('') : '<p class="muted">AI에게 질문하지 않았다.</p>'}
        <p class="muted small">점검 항목은 단어 기준의 간이 판정이다. 실제 채점과 같지 않다.</p>
      </div>
    </div>
  </section>`;
  }).join('')}
</article>`;
  }

  // ---------------------------------------------------------------- 시험 공통
  function confirmBox() {
    const c = state.confirm;
    if (!c) return '';
    return `<div class="confirm-back" role="dialog" aria-modal="true" aria-labelledby="cf-t"><div class="confirm">
      <h2 id="cf-t">${esc(c.title)}</h2><p>${esc(c.body)}</p>
      <div class="row end"><button class="btn" data-act="cf-no">취소</button><button class="btn primary" data-act="cf-yes">${esc(c.yes)}</button></div></div></div>`;
  }

  function afterExamRender() {
    startTicker();
    tick();
    const log = $('#ailog');
    if (log) log.scrollTop = log.scrollHeight;
    const ta = $('#aiinput');
    if (ta && state.exam && state.exam.focusInput) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); state.exam.focusInput = false; }
  }

  function startTicker() { if (!ticker) ticker = setInterval(tick, 500); }
  function stopTicker() { if (ticker) { clearInterval(ticker); ticker = null; } }

  function tick() {
    const ex = state.exam;
    if (!ex) { stopTicker(); return; }
    const s = S();
    const now = Date.now();
    const el = $('#timer');
    const elapsed = now - ex.start;
    if (ex.kind === 'task') {
      const id = ex.tasks[ex.cur];
      ex.taskTime[id] = (ex.taskTime[id] || 0) + (now - ex.lastTick);
      ex.lastTick = now;
      const tc = $('#taskclock');
      if (tc) {
        const used = ex.taskTime[id] || 0;
        tc.innerHTML = `이 과제 <b class="num${used > 22 * 60000 ? ' over' : ''}">${mmss(used)}</b><span class="muted"> / 권장 22:00</span>`;
      }
      const ai = ex.ai[id];
      const btn = $('#aisend');
      if (btn && ai) {
        const left = ai.cool - now;
        if (ai.busy) { btn.disabled = true; }
        else if (left > 0) { btn.disabled = true; btn.textContent = `대기 ${Math.ceil(left / 1000)}초`; }
        else { btn.disabled = ai.left <= 0; btn.textContent = '보내기'; }
      }
    }
    if (el) {
      if (s.noTimer) { el.textContent = '경과 ' + mmss(elapsed); el.className = 'timer'; }
      else {
        const left = ex.duration - elapsed;
        el.textContent = mmss(left);
        el.className = 'timer' + (left < 5 * 60000 ? ' low' : '');
        if (left <= 0) { stopTicker(); ex.kind === 'knowledge' ? finishKnowledge(true) : finishTask(true); return; }
      }
    }
    const pace = $('#pace');
    if (pace && ex.kind === 'knowledge') {
      const expected = Math.min(ex.list.length, Math.floor(elapsed / 90000) + 1);
      pace.innerHTML = `권장 페이스: 지금쯤 <b class="num">${expected}</b>번`;
    }
    if (pace && ex.kind === 'task' && ex.tasks.length > 1) {
      const expected = Math.min(ex.tasks.length, Math.floor(elapsed / (22.5 * 60000)) + 1);
      pace.innerHTML = `권장 페이스: 지금쯤 과제 <b class="num">${expected}</b>`;
    }
  }

  // ---------------------------------------------------------------- 드릴
  function viewDrill(kind) {
    const data = kind === 'verify' ? VD : PD;
    if (!state.drill || state.drill.kind !== kind) state.drill = { kind, i: 0, picked: null, score: 0, done: 0, order: shuffle(data.map((_, i) => i)), perm: data.map((it) => shuffle(it.options.map((_, i) => i))) };
    const d = state.drill;
    if (d.i >= data.length) {
      return page(`<h1>${kind === 'verify' ? 'AI 답변 검증 드릴' : '프롬프트 판단 드릴'} 완료</h1>
        <p class="lede">${d.score} / ${data.length} 정답.</p>
        <div class="row"><button class="btn primary" data-act="drill-restart">처음부터 다시</button><a class="btn" href="#notes">오답노트</a></div>`);
    }
    const item = data[d.order[d.i]];
    const picked = d.picked;
    const intro = kind === 'verify'
      ? 'AI 답변에서 가장 큰 문제를 고른다. 실전에서 AI 출력을 그대로 옮기기 전에 이 감각이 필요하다.'
      : 'AI 어시스트를 어떻게 쓸지 고른다. 정답은 횟수·글자 수·토큰 제약을 함께 고려한 쪽이다.';
    return page(`
      <p class="eyebrow">${kind === 'verify' ? 'AI 답변 검증 드릴' : '프롬프트 판단 드릴'} · ${d.i + 1} / ${data.length}</p>
      <h1>${esc(item.title)}</h1>
      <p class="muted">${intro}</p>
      ${kind === 'verify' ? `<div class="drill-ctx"><span class="muted small">상황</span><pre class="doc-pre">${esc(item.context)}</pre></div>
        <div class="bubble ai solo"><span class="muted small">AI 답변</span><div class="b-text">${esc(item.ai)}</div></div>
        <p><b>이 답변의 가장 큰 문제는?</b></p>` : `<p class="q-stem">${esc(item.stem)}</p>`}
      <div class="opts">${d.perm[d.order[d.i]].map((i, k) => {
        const o = item.options[i];
        let cls = 'opt';
        if (picked != null) { if (i === item.answer) cls += ' right'; else if (i === picked) cls += ' wrong'; }
        return `<button class="${cls}" data-act="drill-pick" data-v="${i}"${picked != null ? ' disabled' : ''}><span class="opt-n">${k + 1}</span><span class="opt-t">${esc(o)}</span></button>`;
      }).join('')}</div>
      ${picked != null ? `<div class="explain ${picked === item.answer ? 'ok' : 'bad'}"><b>${picked === item.answer ? '정답' : '오답'}</b> ${esc(item.why)}</div>
        <div class="row"><button class="btn primary" data-act="drill-next">다음</button></div>` : ''}
      <p class="muted small">점수 ${d.score} / ${d.done}</p>`);
  }

  // ---------------------------------------------------------------- 서술형
  function essayCtx() {
    const e = ESSAYS[0];
    const base = e.useTaskFiles && TMAP[e.useTaskFiles] ? TMAP[e.useTaskFiles].files : [];
    const extra = e.extraFiles.map((f) => Object.assign({ tokens: estTokens(f.text) }, f));
    return { e, files: base.concat(extra) };
  }

  function viewEssay() {
    const s = S();
    const { e, files } = essayCtx();
    if (!state.essay) {
      const saved = store.get('essay-E1', {});
      state.essay = { ai: { left: s.turns, msgs: [], attach: [], sel: [], cool: 0, draft: '', busy: false }, view: files[0].name, text: saved.text || '', checks: saved.checks || {}, showRubric: false, showOutline: false, menu: null };
    }
    const st = state.essay;
    const file = files.find((f) => f.name === st.view) || files[0];
    const total = files.reduce((a, f) => a + f.tokens, 0);
    const lock = s.copyLock ? ' nocopy' : '';
    const att = st.ai.attach.reduce((a, n) => a + ((files.find((f) => f.name === n) || {}).tokens || 0), 0);
    const rubric = e.rubric;
    const scoreOf = (arr) => arr.reduce((a, r) => a + (st.checks[r.k] ? r.pts : 0), 0);
    return `
<article class="doc wide essay">
  <p class="eyebrow">서술형 모의 · 2차 예선 대비</p>
  <h1>${esc(e.title)}</h1>
  <div class="essay-grid">
    <section>
      <p class="${lock}">${esc(e.scenario)}</p>
      <h2>보고서 필수 섹션</h2>
      <ol class="${lock}">${e.sections.map((x) => `<li><b>${esc(x.h)}</b>: ${esc(x.d)}</li>`).join('')}</ol>
      <p class="warn-line"><b>유의사항</b> ${esc(e.caution)}</p>
      <h2>파일 목록 <span class="muted small num">합계 ${fmt(total)}토큰</span></h2>
      <div class="table-wrap filelist"><table class="compact"><thead><tr><th>파일명</th><th class="num">토큰량</th><th></th></tr></thead><tbody>
      ${files.map((f) => { const on = st.ai.attach.includes(f.name); return `<tr class="${f.name === file.name ? 'sel' : ''}"><td><button class="linkish" data-act="e-view" data-f="${esc(f.name)}">${esc(f.name)}</button></td><td class="num">${fmt(f.tokens)}</td><td class="right"><button class="btn tiny${on ? ' on' : ''}" data-act="e-attach" data-f="${esc(f.name)}">${on ? '첨부됨' : 'AI 질문에 추가'}</button></td></tr>`; }).join('')}
      </tbody></table></div>
      <div class="viewer"><div class="viewer-head"><b>${esc(file.name)}</b><span class="num muted">${fmt(file.tokens)} 토큰</span></div><div class="viewer-body${lock}">${renderFile(file)}</div></div>
    </section>
    <section class="assist">
      <div class="ai-head"><b>AI 어시스트</b><span class="ai-left${st.ai.left <= 2 ? ' low' : ''}">${st.ai.left}회 남음</span></div>
      <p class="ai-mode ${s.provider !== 'none' && s.apiKey ? 'live' : 'practice'}">${s.provider !== 'none' && s.apiKey ? `연결됨: ${esc(s.model)}` : '연습 모드: 응답 대신 프롬프트 점검'}</p>
      <div class="ai-log" id="ailog">${st.ai.msgs.length ? st.ai.msgs.map((m, i) => msgBubble(m, i)).join('') : '<p class="ai-empty">1번 문제에 대해 질문해보세요.</p>'}${st.ai.busy ? '<div class="bubble ai"><span class="dots">응답 생성 중</span></div>' : ''}</div>
      <div class="ai-compose">
        <div class="chips"><span class="chip static">첨부 파일 <b>${st.ai.attach.length}</b></span><span class="tok num${att > s.attachCap ? ' over' : ''}">${fmt(att)}/${fmt(s.attachCap)}</span>${st.ai.attach.length ? '<button class="linkish small" data-act="e-att-clear">전체 삭제</button>' : ''}</div>
        <label class="sr-only" for="aiinput">AI에게 보낼 질문</label>
        <textarea id="aiinput" rows="4" placeholder="무엇을 도와드릴까요?" data-act="ai-input">${esc(st.ai.draft)}</textarea>
        <div class="compose-foot"><span class="count num" id="aicount">${fmt(st.ai.draft.length)}/${fmt(s.charCap)}</span><button class="btn primary small" id="aisend" data-act="e-send"${st.ai.left <= 0 || st.ai.busy ? ' disabled' : ''}>보내기</button></div>
      </div>
    </section>
  </div>
  <section class="report">
    <div class="tmpl-head"><h2>최종 제출 보고서</h2><span class="count num" id="essaycount">${fmt(st.text.length)}자</span></div>
    <label class="sr-only" for="essay-text">보고서 본문</label>
    <textarea id="essay-text" rows="16" data-act="essay-text" placeholder="섹션 제목부터 적고 채운다. 결론 → 근거(수치·출처) → 한계 순서.">${esc(st.text)}</textarea>
    <p class="muted small">입력하는 동안 이 브라우저에 자동 저장된다.</p>
    <div class="row"><button class="btn" data-act="go-sol" data-tab="essay">모범 답안·회차별 풀이 보기</button><button class="btn" data-act="e-rubric">${st.showRubric ? '채점표 닫기' : '자가 채점표 열기'}</button><button class="btn" data-act="e-outline">${st.showOutline ? '모범 개요 닫기' : '모범 답안 개요 보기'}</button>
    ${s.provider !== 'none' && s.apiKey ? '<button class="btn" data-act="e-feedback">AI 피드백 받기 (횟수 미차감)</button>' : ''}</div>
    ${st.showRubric ? `<div class="two-col">
      <div class="panel"><h3>결과 평가 <span class="num muted">${scoreOf(rubric.result)}/50</span></h3>${rubric.result.map((r) => `<label class="rub"><input type="checkbox" id="rub-${r.k}" data-act="rub" data-k="${r.k}"${st.checks[r.k] ? ' checked' : ''}> <span>${esc(r.t)}</span></label>`).join('')}</div>
      <div class="panel"><h3>과정 평가 <span class="num muted">${scoreOf(rubric.process)}/50</span></h3>${rubric.process.map((r) => `<label class="rub"><input type="checkbox" id="rub-${r.k}" data-act="rub" data-k="${r.k}"${st.checks[r.k] ? ' checked' : ''}> <span>${esc(r.t)}</span></label>`).join('')}</div>
    </div><p class="muted small">채점표는 체험판 안내문의 결과·과정 기준을 이 과제에 맞게 풀어 쓴 것이다.</p>` : ''}
    ${st.showOutline ? `<div class="panel"><h3>모범 답안 개요</h3><ol>${e.outline.map((o) => `<li>${esc(o)}</li>`).join('')}</ol></div>` : ''}
    ${st.feedback ? `<div class="panel"><h3>AI 피드백</h3><div class="b-text">${esc(st.feedback)}</div></div>` : ''}
  </section>
</article>`;
  }

  function afterEssayRender() {
    const log = $('#ailog');
    if (log) log.scrollTop = log.scrollHeight;
    if (state.essay && state.essay.focusInput) { const ta = $('#aiinput'); if (ta) ta.focus(); state.essay.focusInput = false; }
    startEssayTicker();
  }
  let essayTicker = null;
  function startEssayTicker() {
    if (essayTicker) return;
    essayTicker = setInterval(() => {
      if (route() !== 'essay' || state.exam || !state.essay) { clearInterval(essayTicker); essayTicker = null; return; }
      const btn = $('#aisend');
      const ai = state.essay.ai;
      if (!btn) return;
      const left = ai.cool - Date.now();
      if (ai.busy) btn.disabled = true;
      else if (left > 0) { btn.disabled = true; btn.textContent = `대기 ${Math.ceil(left / 1000)}초`; }
      else { btn.disabled = ai.left <= 0; btn.textContent = '보내기'; }
    }, 500);
  }

  // ---------------------------------------------------------------- 정답·풀이 가이드
  function tbl(x) {
    return `<div class="table-wrap"><table class="compact"><caption>${esc(x.caption)}</caption>
      <thead><tr>${x.headers.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead>
      <tbody>${x.rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  // 지식평가 한 문항의 풀이: 단서 → 보기별 정오 이유 → 정리
  function kExplain(q, user) {
    let body = '';
    if (q.type === 'mc') {
      body = `<ol class="opt-review">${q.options.map((o, i) => {
        const ok = i === q.answer;
        const mine = user === i && !ok;
        return `<li class="${ok ? 'ok' : 'no'}${mine ? ' mine' : ''}"><span class="mark">${ok ? '정답' : mine ? '내 선택' : '오답'}</span>
          <span class="o">${esc(o)}</span><span class="r">${esc((q.elim || [])[i] || '')}</span></li>`;
      }).join('')}</ol>`;
    } else if (q.type === 'ox') {
      body = `<p class="ox-ans">정답 <b>${q.answer}</b></p>`;
    } else {
      body = `<p class="ox-ans">정답 <b>${esc(q.answer[0])}</b>${q.answer.length > 1 ? ` <span class="muted small">(인정: ${q.answer.slice(1).map(esc).join(', ')})</span>` : ''}</p>${q.calc ? `<p class="calc"><b>풀이</b> ${esc(q.calc)}</p>` : ''}`;
    }
    return `${q.clue ? `<p class="clue"><b>먼저 볼 단서</b> ${esc(q.clue)}</p>` : ''}${body}
      <p><b>정리</b> ${esc(q.why)}</p>${q.trap ? `<p class="trap-line"><b>함정</b> ${esc(q.trap)}</p>` : ''}${srcList(q.src)}`;
  }

  function turnCard(turn, fileTok, idp) {
    const s = S();
    const tok = turn.attach.reduce((a, n) => a + (fileTok[n] || 0), 0);
    const pid = `${idp}-t${turn.n}`;
    return `<section class="turn">
      <div class="turn-head"><span class="turn-n">${turn.n}회차</span><b>${esc(turn.title)}</b></div>
      <div class="turn-grid">
        ${turn.select ? `<div><span class="lab">‘문제’ 버튼에서 선택</span><div>${turn.select.length ? turn.select.map((n) => `<span class="pill">${n}번</span>`).join('') : '<span class="muted">선택 없음</span>'}</div></div>` : ''}
        <div><span class="lab">‘AI 질문에 추가’로 첨부</span>${turn.attach.length
          ? `<ul class="att">${turn.attach.map((n) => `<li><span>${esc(n)}</span><span class="num">${fmt(fileTok[n] || 0)}</span></li>`).join('')}</ul><div class="att-sum num${tok > s.attachCap ? ' over' : ''}">합계 ${fmt(tok)} / ${fmt(s.attachCap)} 토큰</div>`
          : '<div class="muted">첨부 없음 (필요한 숫자는 프롬프트에 직접 적는다)</div>'}</div>
      </div>
      <div class="lab-row"><span class="lab">입력창에 칠 프롬프트</span><span class="num muted small">${fmt(turn.prompt.length)} / ${fmt(s.charCap)}자</span><button class="btn tiny" data-act="copy-pre" data-target="${pid}">복사 (연습용)</button></div>
      <pre class="tmpl" id="${pid}">${esc(turn.prompt)}</pre>
      <p class="why-line"><b>이렇게 쓴 이유</b> ${esc(turn.why)}</p>
      <span class="lab">AI 답에서 나와야 하는 값</span>
      ${turn.expect.map(tbl).join('')}
      <span class="lab">받은 답에서 확인할 것</span>
      <ul class="checks">${turn.checks.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>
    </section>`;
  }

  function renderWalkTask(t) {
    const w = t.walk;
    if (!w) return '<p class="muted">풀이 데이터가 없다.</p>';
    const fileTok = Object.fromEntries(t.files.map((f) => [f.name, f.tokens]));
    return `<div class="walk-body">
      <p class="goal">${esc(w.goal)}</p>
      <h3>1. 문항 4개를 먼저 읽고 필요한 것 적기</h3>
      ${tbl({ caption: '문항별로 필요한 판정·계산과 근거 자료', headers: ['문항', '필요한 것', '볼 자료'], rows: w.reading.map((r) => [r.q, r.need, r.src]) })}
      <h3>2. 첨부 계획 (파일 목록 토큰량 확인)</h3>
      <p>${esc(w.plan)}</p>
      ${w.batches ? tbl({ caption: '동호회 묶음', headers: ['묶음', '동호회', '토큰'], rows: w.batches.map((b) => [b.label, b.clubs.join(', '), fmt(b.tokens)]) }) : ''}
      <details class="mini"><summary>파일별 토큰량 (합계 ${fmt(t.totalTokens)})</summary>
        ${tbl({ caption: '파일 목록', headers: ['파일명', '토큰량'], rows: t.files.map((f) => [f.name, fmt(f.tokens)]) })}</details>
      <h3>3. 회차별 진행</h3>
      ${w.turns.map((turn) => turnCard(turn, fileTok, `w-${t.id}`)).join('')}
      ${w.manual ? `<section class="turn manual"><div class="turn-head"><span class="turn-n">손</span><b>${esc(w.manual.title)}</b></div><p>${esc(w.manual.text)}</p>${w.manual.tables.map(tbl).join('')}</section>` : ''}
      <h3>4. 답 입력</h3>
      ${tbl({ caption: '최종 답과 검산', headers: ['문항', '정답', '어떻게 나왔나'], rows: w.final.map((f) => [f.q, f.answer, f.how]) })}
      <p class="muted small">${esc(w.usage)}</p>
    </div>`;
  }

  function viewSolutions() {
    if (!state.sol) state.sol = { tab: 'task', task: 'T1', kset: 'A' };
    const sol = state.sol;
    const tabs = [['task', '활용평가 회차별 풀이'], ['knowledge', '지식평가 보기별 해설'], ['essay', '서술형 모범답안']];
    let body = '';
    if (sol.tab === 'task') {
      const t = TMAP[sol.task] || TASKS[0];
      body = `<div class="seg sub" role="tablist">${TASKS.map((x, i) => `<button role="tab" class="seg-btn${x.id === t.id ? ' on' : ''}" aria-selected="${x.id === t.id}" data-act="sol-task" data-task="${x.id}">과제 ${i + 1}. ${esc(x.title)}</button>`).join('')}</div>
        <h2>${esc(t.title)}</h2>
        <p class="muted">${esc(t.scenario)}</p>
        ${renderWalkTask(t)}`;
    } else if (sol.tab === 'knowledge') {
      const sets = window.KNOWLEDGE_SETS || {};
      const ids = sol.kset === 'ALL' ? K.map((q) => q.id) : (sets[sol.kset] || []);
      body = `<div class="seg sub" role="tablist">${[['A', '세트 A'], ['B', '세트 B'], ['ALL', `전체 ${K.length}문항`]].map(([k, l]) => `<button role="tab" class="seg-btn${sol.kset === k ? ' on' : ''}" aria-selected="${sol.kset === k}" data-act="sol-kset" data-set="${k}">${l}</button>`).join('')}</div>
        <p class="muted">지식평가는 AI를 쓰지 않는 세션이다. 풀이 순서는 ‘질문 문장 → 보기 차이 → 지문 단서’다. 문항마다 먼저 볼 단서와 보기별로 맞고 틀린 이유를 붙였다.</p>
        <div class="row"><button class="btn small" data-act="sol-open-all">모두 펼치기</button><button class="btn small" data-act="sol-close-all">모두 접기</button></div>
        ${ids.map((id, i) => { const q = KMAP[id]; return q ? `<details class="review sol"><summary><b>${i + 1}.</b> ${esc(q.area)} <span class="muted">· ${qTypeLabel(q)} · ${q.id}</span></summary><p class="q-stem">${esc(q.stem)}</p>${kExplain(q)}</details>` : ''; }).join('')}`;
    } else {
      const { e, files } = essayCtx();
      const w = e.walk;
      const fileTok = Object.fromEntries(files.map((f) => [f.name, f.tokens]));
      body = `<h2>${esc(e.title)}</h2>
        <p class="goal">${esc(w.goal)}</p>
        <h3>1. 회차 계획</h3>
        ${tbl({ caption: '회차별 목적과 첨부', headers: ['회차', '목적', '첨부', '쓰는 곳'], rows: w.plan })}
        <h3>2. 회차별 진행</h3>
        ${w.turns.map((turn) => turnCard(turn, fileTok, 'w-E1')).join('')}
        <section class="turn manual"><div class="turn-head"><span class="turn-n">손</span><b>비식별 최종 점검</b></div><ul class="checks">${w.deid.map((d) => `<li>${esc(d)}</li>`).join('')}</ul></section>
        <h3>3. 모범 보고서 전문</h3>
        <div class="row"><span class="num muted small">${fmt(e.model.length)}자</span><button class="btn tiny" data-act="copy-pre" data-target="model-E1">복사 (연습용)</button></div>
        <pre class="report-pre" id="model-E1">${esc(e.model)}</pre>
        <h3>4. 채점표 항목별로 어디서 점수를 받는지</h3>
        ${tbl({ caption: '채점 항목 ↔ 풀이 단계', headers: ['채점 항목', '해당 단계'], rows: w.rubricMap })}
        <p class="muted small">${esc(w.usage)}</p>`;
    }
    return `<article class="doc wide">
      <p class="eyebrow">정답·풀이 가이드</p>
      <h1>어떻게 첨부하고, 무엇을 물어야 하나</h1>
      <p class="warn-line"><b>먼저 풀고 볼 것.</b> 정답과 프롬프트 전문이 다 나온다. 모의고사를 한 번 풀어 본 뒤 내 프롬프트 기록과 비교하는 용도로 쓴다.</p>
      <div class="seg" role="tablist">${tabs.map(([k, l]) => `<button role="tab" class="seg-btn${sol.tab === k ? ' on' : ''}" aria-selected="${sol.tab === k}" data-act="sol-tab" data-tab="${k}">${l}</button>`).join('')}</div>
      ${body}
    </article>`;
  }

  // ---------------------------------------------------------------- 오답노트
  function viewNotes() {
    const wk = store.get('wrongK', {});
    const wt = store.get('wrongT', {});
    const kIds = Object.keys(wk).filter((id) => KMAP[id]).sort((a, b) => wk[b] - wk[a]);
    const tIds = Object.keys(wt);
    const tq = {};
    TASKS.forEach((t) => t.questions.forEach((q) => { tq[q.id] = { q, t }; }));
    return page(`<h1>오답노트</h1>
      <p class="lede">틀린 문항이 자동으로 쌓인다. 이해했으면 ‘지우기’를 누른다.</p>
      <h2>지식평가 <span class="muted">${kIds.length}문항</span></h2>
      ${kIds.length ? `<div class="row"><button class="btn primary" data-act="retry-notes">오답만 모의고사로 풀기 (문항당 90초)</button></div>
      ${kIds.map((id) => { const q = KMAP[id]; return `<details class="review bad"><summary><span class="badge bad">${wk[id]}회</span> ${esc(q.area)} · ${esc(q.stem.slice(0, 60))}…</summary>
        <p class="q-stem">${esc(q.stem)}</p><p><b>정답</b> ${esc(q.type === 'mc' ? q.options[q.answer] : q.type === 'ox' ? q.answer : q.answer[0])}</p><p>${esc(q.why)}</p>${q.trap ? `<p class="trap-line"><b>함정</b> ${esc(q.trap)}</p>` : ''}${srcList(q.src)}
        <button class="btn tiny" data-act="note-del" data-kind="K" data-id="${id}">지우기</button></details>`; }).join('')}` : '<p class="muted">아직 없다.</p>'}
      <h2>활용평가 <span class="muted">${tIds.length}문항</span></h2>
      ${tIds.length ? tIds.filter((id) => tq[id]).map((id) => { const { q, t } = tq[id]; return `<details class="review bad"><summary><span class="badge bad">${wt[id]}회</span> ${esc(t.title)} · ${esc(q.prompt)}</summary>
        <p><b>정답</b> ${esc(q.type === 'mc' ? q.options[q.answer] : q.answer)}</p><p>${esc(q.why)}</p><p class="trap-line"><b>함정</b> ${esc(q.trap)}</p>
        <button class="btn tiny" data-act="note-del" data-kind="T" data-id="${id}">지우기</button></details>`; }).join('') : '<p class="muted">아직 없다.</p>'}`);
  }

  // ---------------------------------------------------------------- 설정
  function viewSettings() {
    const s = S();
    const opt = (v, l) => `<label class="radio"><input type="radio" name="prov" id="prov-${v}" value="${v}" data-act="set-prov"${s.provider === v ? ' checked' : ''}> ${l}</label>`;
    const ph = { openai: '예: gpt-4.1-mini (계정에서 쓸 수 있는 모델명)', anthropic: '예: claude-haiku-5-5', gemini: '예: gemini-2.5-flash', none: '' }[s.provider];
    return page(`<h1>설정 · AI 연결</h1>
      <h2>AI 어시스트 연결 (선택)</h2>
      <p>본인 API 키를 넣으면 모의고사의 AI 어시스트가 실제 응답을 준다. 키는 이 브라우저의 저장소에만 남고 이 사이트의 서버로 보내지 않는다. 남의 컴퓨터에서는 넣지 말 것. claude.ai 미리보기 화면에서는 외부 호출이 막혀서, 깃허브 코드를 로컬이나 Vercel로 열어야 동작한다.</p>
      <div class="radio-row">${opt('none', '연결 안 함 (연습 모드)')}${opt('openai', 'OpenAI')}${opt('anthropic', 'Anthropic')}${opt('gemini', 'Google Gemini')}</div>
      ${s.provider !== 'none' ? `
      <label class="field"><span>API 키</span><input id="set-key" type="password" autocomplete="off" value="${esc(s.apiKey)}" data-act="set-field" data-k="apiKey"></label>
      <label class="field"><span>모델 이름</span><input id="set-model" type="text" autocomplete="off" value="${esc(s.model)}" placeholder="${esc(ph)}" data-act="set-field" data-k="model"></label>
      <div class="row"><button class="btn" data-act="set-test">연결 확인 (짧은 요청 1회)</button><span id="set-test-out" class="muted small"></span></div>` : ''}
      <h2>시험 환경 흉내</h2>
      <div class="set-grid">
        <label class="field"><span>과제당 AI 질문 횟수</span><input id="set-turns" type="number" min="1" max="50" value="${s.turns}" data-act="set-num" data-k="turns"></label>
        <label class="field"><span>질문 후 대기(초)</span><input id="set-cool" type="number" min="0" max="120" value="${s.cooldown}" data-act="set-num" data-k="cooldown"></label>
        <label class="field"><span>질문 1회 첨부 한도(토큰)</span><input id="set-cap" type="number" min="1000" max="200000" step="1000" value="${s.attachCap}" data-act="set-num" data-k="attachCap"></label>
        <label class="field"><span>입력창 글자 수 한도</span><input id="set-char" type="number" min="100" max="10000" step="100" value="${s.charCap}" data-act="set-num" data-k="charCap"></label>
      </div>
      <label class="toggle"><input type="checkbox" id="set-clear" data-act="set-bool" data-k="clearAttach"${s.clearAttach ? ' checked' : ''}> 질문을 보내면 첨부를 비운다 (다음 질문에 파일이 따라오지 않는 상황 연습)</label>
      <label class="toggle"><input type="checkbox" id="set-hist" data-act="set-bool" data-k="keepHistory"${s.keepHistory ? ' checked' : ''}> 이전 질문·응답 텍스트를 다음 요청에 포함 (파일 내용은 제외)</label>
      <label class="toggle"><input type="checkbox" id="set-copy" data-act="set-bool" data-k="copyLock"${s.copyLock ? ' checked' : ''}> 지문·첨부 뷰어 복사 막기</label>
      <label class="toggle"><input type="checkbox" id="set-notimer" data-act="set-bool" data-k="noTimer"${s.noTimer ? ' checked' : ''}> 시간 제한 없이 연습 (경과 시간만 표시)</label>
      <h2>기록</h2>
      <p class="muted">모의고사 기록, 오답노트, 체크 상태, 서술형 초안을 지운다. 설정은 남는다.</p>
      <button class="btn danger" data-act="reset-ask">학습 기록 지우기</button>
      ${state.confirm ? confirmBox() : ''}`);
  }

  async function testConnection() {
    const out = $('#set-test-out');
    if (out) out.textContent = '확인 중…';
    try {
      const r = await callAI([{ role: 'user', content: '연결 확인입니다. "확인"이라고만 답하세요.' }], '짧게 답하세요.');
      if (out) out.textContent = '응답: ' + String(r).slice(0, 60);
    } catch (e) {
      if (out) out.textContent = '실패: ' + (e.message || e);
    }
  }

  // ---------------------------------------------------------------- 이벤트
  document.addEventListener('click', (ev) => {
    const el = ev.target.closest('[data-act]');
    if (el && el.tagName === 'INPUT' && (el.type === 'radio' || el.type === 'checkbox')) return; // change 이벤트에서 처리
    if (!el) {
      if (state.exam && state.exam.menu && !ev.target.closest('.pop-wrap')) { state.exam.menu = null; render(); }
      return;
    }
    const act = el.dataset.act;
    const ex = state.exam;
    switch (act) {
      case 'start-k': startKnowledge(el.dataset.set); break;
      case 'start-t': startTask(el.dataset.tasks.split(','), +el.dataset.min); break;
      case 'quit': state.confirm = { title: '그만둘까요?', body: '지금까지 푼 내용은 채점하지 않고 버린다.', yes: '그만두기', on: () => { state.exam = null; state.confirm = null; stopTicker(); render(); } }; render(); break;
      case 'submit-ask': {
        let n = 0, total = 0;
        if (ex.kind === 'knowledge') { total = ex.list.length; n = ex.list.filter((x) => ex.answers[x] != null && ex.answers[x] !== '').length; }
        else { const qs = ex.tasks.flatMap((id) => TMAP[id].questions); total = qs.length; n = qs.filter((q) => ex.answers[q.id] != null && ex.answers[q.id] !== '').length; }
        state.confirm = { title: '채점 후 종료할까요?', body: `${total}문제 중 ${n}문제에 답했다.${n < total ? ' 답하지 않은 문제는 오답 처리된다.' : ''}`, yes: '채점하기', on: () => { state.confirm = null; ex.kind === 'knowledge' ? finishKnowledge(false) : finishTask(false); } };
        render(); break;
      }
      case 'cf-yes': { const c = state.confirm; if (c && c.on) c.on(); break; }
      case 'cf-no': state.confirm = null; render(); break;
      case 'k-go': ex.idx = +el.dataset.i; render(); break;
      case 'k-prev': ex.idx = Math.max(0, ex.idx - 1); render(); break;
      case 'k-next': ex.idx = Math.min(ex.list.length - 1, ex.idx + 1); render(); break;
      case 'k-flag': { const id = ex.list[ex.idx]; ex.flags[id] = !ex.flags[id]; render(); break; }
      case 'result-close': { const k = state.result.kind; state.result = null; location.hash = k === 'knowledge' ? 'mock-knowledge' : 'mock-task'; render(); break; }
      case 'retry-wrong-k': { const ids = state.result.items.filter((x) => !x.ok).map((x) => x.id); startKnowledge(null, ids); break; }
      case 'retry-notes': { const ids = Object.keys(store.get('wrongK', {})).filter((id) => KMAP[id]); if (ids.length) startKnowledge(null, ids); break; }
      case 'note-del': { const key = el.dataset.kind === 'K' ? 'wrongK' : 'wrongT'; const o = store.get(key, {}); delete o[el.dataset.id]; store.set(key, o); render(); break; }
      case 't-go': ex.cur = +el.dataset.i; ex.menu = null; ex.err = ''; ex.lastTick = Date.now(); render(); $('#passage') && ($('#passage').scrollTop = 0); break;
      case 't-prev': ex.cur = Math.max(0, ex.cur - 1); ex.menu = null; ex.err = ''; render(); break;
      case 't-next': ex.cur = Math.min(ex.tasks.length - 1, ex.cur + 1); ex.menu = null; ex.err = ''; render(); break;
      case 't-jump': { ex.cur = +el.dataset.ti; ex.menu = null; render(); const q = document.getElementById('q-' + el.dataset.q); if (q) q.scrollIntoView({ block: 'start' }); break; }
      case 't-view': ex.view[curTask().id] = el.dataset.f; render(); break;
      case 't-attach': {
        const t = curTask(); const ai = ex.ai[t.id]; const n = el.dataset.f; const s = S();
        if (ai.attach.includes(n)) { ai.attach = ai.attach.filter((x) => x !== n); ex.err = ''; }
        else {
          const cur = ai.attach.reduce((a, x) => a + (t.files.find((f) => f.name === x) || { tokens: 0 }).tokens, 0);
          const add = (t.files.find((f) => f.name === n) || { tokens: 0 }).tokens;
          if (cur + add > s.attachCap) ex.err = `첨부 한도를 넘는다: 지금 ${fmt(cur)} + ${fmt(add)} = ${fmt(cur + add)} > ${fmt(s.attachCap)}토큰. 묶음을 나눠서 질문해야 한다.`;
          else { ai.attach.push(n); ex.err = ''; }
        }
        render(); break;
      }
      case 'att-clear': ex.ai[curTask().id].attach = []; ex.err = ''; render(); break;
      case 'menu': ex.menu = (el.dataset.m && ex.menu !== el.dataset.m) ? el.dataset.m : null; render(); break;
      case 'sel-all': { const t = curTask(); ex.ai[t.id].sel = t.questions.map((q) => q.id); render(); break; }
      case 't-flag': ex.flags[el.dataset.q] = !ex.flags[el.dataset.q]; render(); break;
      case 'to-top': { const p = $('#passage'); if (p) p.scrollTo({ top: 0 }); window.scrollTo({ top: 0 }); break; }
      case 'ai-send': {
        const t = curTask(); const ai = ex.ai[t.id];
        ex.menu = null;
        sendAI(t, ai, { qBase: ex.tasks.indexOf(t.id) * 4, rerender: () => { if (state.exam) { state.exam.focusInput = true; render(); } } });
        break;
      }
      case 'copy-msg': {
        const holder = state.exam ? state.exam.ai[curTask().id] : state.essay && state.essay.ai;
        const m = holder && holder.msgs[+el.dataset.i];
        if (m && m.copy != null) copyText(m.copy, el);
        break;
      }
      case 'drill-pick': { const d = state.drill; if (d.picked == null) { d.picked = +el.dataset.v; const data = d.kind === 'verify' ? VD : PD; const item = data[d.order[d.i]]; d.done++; if (d.picked === item.answer) d.score++; else { const w = store.get('wrongD', {}); w[item.id] = (w[item.id] || 0) + 1; store.set('wrongD', w); } render(); } break; }
      case 'drill-next': state.drill.i++; state.drill.picked = null; render(); break;
      case 'drill-restart': state.drill = null; render(); break;
      case 'copy-el': { const ta = document.getElementById(el.dataset.target); if (ta) copyText(ta.value, el); break; }
      case 'e-view': state.essay.view = el.dataset.f; render(); break;
      case 'e-attach': {
        const { files } = essayCtx(); const ai = state.essay.ai; const n = el.dataset.f; const s = S();
        if (ai.attach.includes(n)) ai.attach = ai.attach.filter((x) => x !== n);
        else {
          const cur = ai.attach.reduce((a, x) => a + ((files.find((f) => f.name === x) || {}).tokens || 0), 0);
          const add = (files.find((f) => f.name === n) || {}).tokens || 0;
          if (cur + add > s.attachCap) toast(`첨부 한도 초과: ${fmt(cur + add)} > ${fmt(s.attachCap)}토큰`); else ai.attach.push(n);
        }
        render(); break;
      }
      case 'e-att-clear': state.essay.ai.attach = []; render(); break;
      case 'e-send': {
        const { files } = essayCtx();
        sendAI({ files, scenario: ESSAYS[0].scenario, cautions: [ESSAYS[0].caution], questions: [] }, state.essay.ai, { essay: true, rerender: () => { state.essay.focusInput = true; render(); } });
        break;
      }
      case 'e-rubric': state.essay.showRubric = !state.essay.showRubric; render(); break;
      case 'e-outline': state.essay.showOutline = !state.essay.showOutline; render(); break;
      case 'e-feedback': essayFeedback(el); break;
      case 'set-test': testConnection(); break;
      case 'sol-tab': state.sol.tab = el.dataset.tab; render(); break;
      case 'sol-task': state.sol.task = el.dataset.task; render(); break;
      case 'sol-kset': state.sol.kset = el.dataset.set; render(); break;
      case 'sol-open-all': $$('details.sol').forEach((d) => { d.open = true; }); break;
      case 'sol-close-all': $$('details.sol').forEach((d) => { d.open = false; }); break;
      case 'copy-pre': { const src = document.getElementById(el.dataset.target); if (src) copyText(src.textContent, el); break; }
      case 'go-sol': {
        state.sol = Object.assign(state.sol || { tab: 'task', task: 'T1', kset: 'A' }, { tab: el.dataset.tab || 'task' }, el.dataset.task ? { task: el.dataset.task } : {});
        state.result = null;
        if (route() === 'solutions') render(); else location.hash = 'solutions';
        break;
      }
      case 'reset-ask': state.confirm = { title: '학습 기록을 지울까요?', body: '모의고사 기록, 오답노트, 체크 상태, 서술형 초안이 지워진다.', yes: '지우기', on: () => { ['attempts', 'wrongK', 'wrongT', 'wrongD', 'todo', 'check', 'essay-E1'].forEach(store.del); state.confirm = null; state.essay = null; toast('지웠다.'); render(); } }; render(); break;
      default: break;
    }
  });

  document.addEventListener('change', (ev) => {
    const el = ev.target.closest('[data-act]');
    if (!el) return;
    const act = el.dataset.act;
    const ex = state.exam;
    switch (act) {
      case 'k-pick': { const id = ex.list[ex.idx]; const q = KMAP[id]; ex.answers[id] = q.type === 'mc' ? +el.dataset.v : el.dataset.v; render(); break; }
      case 't-pick': ex.answers[el.dataset.q] = +el.dataset.v; render(); break;
      case 'sel-q': { const ai = ex.ai[curTask().id]; const q = el.dataset.q; ai.sel = el.checked ? Array.from(new Set(ai.sel.concat(q))) : ai.sel.filter((x) => x !== q); render(); break; }
      case 'todo': { const o = store.get('todo', {}); o[el.dataset.k] = el.checked; store.set('todo', o); break; }
      case 'check': { const o = store.get('check', {}); o[el.dataset.k] = el.checked; store.set('check', o); break; }
      case 'rub': { state.essay.checks[el.dataset.k] = el.checked; saveEssay(); render(); break; }
      case 'set-prov': { const s = S(); s.provider = el.value; store.set('settings', Object.assign(store.get('settings', {}), { provider: el.value })); render(); break; }
      case 'set-field': { const o = store.get('settings', {}); o[el.dataset.k] = el.value.trim(); store.set('settings', o); break; }
      case 'set-num': { const o = store.get('settings', {}); const v = parseInt(el.value, 10); if (!isNaN(v)) { o[el.dataset.k] = v; store.set('settings', o); } break; }
      case 'set-bool': { const o = store.get('settings', {}); o[el.dataset.k] = el.checked; store.set('settings', o); break; }
      default: break;
    }
  });

  document.addEventListener('input', (ev) => {
    const el = ev.target;
    const act = el.dataset && el.dataset.act;
    if (!act) { if (el.dataset && el.dataset.counter) updateTemplateCounts(); return; }
    const ex = state.exam;
    switch (act) {
      case 'k-short': ex.answers[ex.list[ex.idx]] = el.value; refreshKCounts(); break;
      case 't-short': ex.answers[el.dataset.q] = el.value; refreshTCounts(); break;
      case 'ai-input': {
        const ai = state.exam ? state.exam.ai[curTask().id] : state.essay.ai;
        ai.draft = el.value;
        const c = $('#aicount'); const cap = S().charCap;
        if (c) { c.textContent = `${fmt(el.value.length)}/${fmt(cap)}`; c.classList.toggle('over', el.value.length > cap); }
        break;
      }
      case 'essay-text': state.essay.text = el.value; const c = $('#essaycount'); if (c) c.textContent = `${fmt(el.value.length)}자`; saveEssay(); break;
      case 'cheat-filter': {
        const q = el.value.trim().toLowerCase();
        $$('table.cheat tbody tr').forEach((tr) => { tr.hidden = q && !tr.textContent.toLowerCase().includes(q); });
        break;
      }
      default: if (el.dataset.counter) updateTemplateCounts();
    }
  });

  function refreshKCounts() {
    const ex = state.exam;
    const n = ex.list.filter((x) => ex.answers[x] != null && ex.answers[x] !== '').length;
    const f = $('.exam-foot .muted b'); if (f) f.textContent = n;
    const btn = $$('.qnav-grid .qn')[ex.idx];
    if (btn) btn.classList.toggle('done', !!ex.answers[ex.list[ex.idx]]);
  }
  function refreshTCounts() {
    const ex = state.exam;
    const qs = ex.tasks.flatMap((id) => TMAP[id].questions);
    const n = qs.filter((q) => ex.answers[q.id] != null && ex.answers[q.id] !== '').length;
    const f = $('.exam-foot .muted b'); if (f) f.textContent = n;
    $$('.qnav .qn').forEach((b) => { const id = b.dataset.q; b.classList.toggle('done', !!(ex.answers[id] != null && ex.answers[id] !== '')); });
  }

  let essaySaveTimer = null;
  function saveEssay() {
    clearTimeout(essaySaveTimer);
    essaySaveTimer = setTimeout(() => { if (state.essay) store.set('essay-E1', { text: state.essay.text, checks: state.essay.checks }); }, 300);
  }

  async function essayFeedback(btn) {
    const st = state.essay; const e = ESSAYS[0];
    if (!st.text.trim()) { toast('보고서를 먼저 쓴다.'); return; }
    btn.disabled = true; btn.textContent = '피드백 받는 중…';
    const rub = e.rubric.result.concat(e.rubric.process).map((r) => `- ${r.t} (${r.pts}점)`).join('\n');
    const prompt = `다음은 연습용 서술형 보고서다. 채점표 항목마다 충족/부분/미충족과 이유를 한 줄씩 쓰고, 고칠 점 3가지를 제시해라. 점수는 매기지 말고, 보고서에 없는 사실은 지어내지 마라.\n\n[과제]\n${e.scenario}\n필수 섹션: ${e.sections.map((x) => x.h).join(', ')}\n\n[채점표]\n${rub}\n\n[보고서]\n${st.text}`;
    try { st.feedback = await callAI([{ role: 'user', content: prompt }], '당신은 엄격한 보고서 검토자입니다. 한국어로 간결하게 답합니다.'); }
    catch (err) { st.feedback = '피드백 요청 실패: ' + (err.message || err); }
    render();
  }

  // ---------------------------------------------------------------- 복사 막기 (지문·첨부 뷰어)
  ['copy', 'cut'].forEach((type) => document.addEventListener(type, (ev) => {
    if (!S().copyLock) return;
    const sel = window.getSelection();
    const node = sel && sel.anchorNode && (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement);
    if (node && node.closest && node.closest('.nocopy')) { ev.preventDefault(); toast('지문과 첨부 파일은 복사할 수 없다 (실제 시험과 같은 제한). 설정에서 끌 수 있다.'); }
  }));
  document.addEventListener('contextmenu', (ev) => { if (S().copyLock && ev.target.closest && ev.target.closest('.nocopy')) ev.preventDefault(); });

  // ---------------------------------------------------------------- 키보드
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') {
      if (state.confirm) { state.confirm = null; render(); return; }
      if (state.exam && state.exam.menu) { state.exam.menu = null; render(); return; }
      if (document.body.classList.contains('nav-open')) { document.body.classList.remove('nav-open'); }
    }
    if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && ev.target.id === 'aiinput') {
      ev.preventDefault();
      const b = $('#aisend'); if (b && !b.disabled) b.click();
    }
  });

  // ---------------------------------------------------------------- 셸
  function initShell() {
    const menuBtn = $('#menu-btn');
    if (menuBtn) menuBtn.addEventListener('click', () => { const open = document.body.classList.toggle('nav-open'); menuBtn.setAttribute('aria-expanded', String(open)); });
    document.addEventListener('click', (ev) => {
      const a = ev.target.closest('a[href^="#"]');
      if (!a) return;
      document.body.classList.remove('nav-open');
      // 같은 주소를 다시 누르면 hashchange가 안 생기므로 결과·드릴 화면을 직접 닫는다
      if (!state.exam && a.getAttribute('href') === (location.hash || '#home')) { state.result = null; state.drill = null; render(); }
    });
    const themeBtn = $('#theme-btn');
    const applyTheme = (t) => { if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme'); };
    applyTheme(store.get('theme', null));
    if (themeBtn) themeBtn.addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      const next = cur === 'dark' ? 'light' : 'dark';
      applyTheme(next); store.set('theme', next);
    });
    window.addEventListener('hashchange', () => { if (!state.exam) { state.result = null; if (route() !== 'drill-verify' && route() !== 'drill-prompt') state.drill = null; } render(); });
    window.addEventListener('beforeunload', (ev) => { if (state.exam) { ev.preventDefault(); ev.returnValue = ''; } });
  }

  initShell();
  render();
})();
