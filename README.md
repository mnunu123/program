# 하이닉스 1차 대비 노트

SK하이닉스 AI 해커톤 2026 1차 예선(프로그래머스 AI 역량평가 환경)을 준비하기 위한 개인 학습용 웹사이트.
유형별 단계 가이드와, 실제 시험 화면의 제약을 흉내 낸 모의고사가 들어 있다.

> 문항과 데이터는 모두 자체 제작이다. 프로그래머스 공식 기출·체험 문항을 옮기지 않았다.
> 시험 정보는 2026-10-17 기준으로 공식 공고, 프로그래머스 공식 체험판, 공개 영상, 기사에서 모았다. 안내 메일이 오면 그 내용이 우선이다.

## 바로 열기

```bash
npm start            # 또는 node server.js  → http://localhost:3000
```

Node 18 이상이면 설치할 패키지가 없다. 서버 없이 `dist/index.html`을 더블클릭해도 열린다(한 파일로 묶은 버전).

### Vercel에 올리기

1. Vercel에서 이 저장소를 Import
2. Framework Preset: **Other**, Build Command: 비움, Output Directory: 비움(루트)
3. Deploy → 루트의 `index.html`이 그대로 서비스된다

GitHub Pages를 쓰려면 저장소 Settings → Pages → Branch `main` / `/ (root)`.

## 들어 있는 것

| 메뉴 | 내용 |
|---|---|
| 시험 정보 | 일정, 세션 구성(20문항 30분 + 16문항 90분), AI 어시스트 규칙, 채점 방식. 항목마다 출처 태그 |
| 유형별 가이드 | 객관식·O/X, 단답형, AI 과제형, 서술형을 단계별로 |
| 프롬프트 템플릿 | 1,000자 안에 들어가는 1차 프롬프트 뼈대 5종, 글자 수 세기 |
| 지식평가 모의고사 | 52문항 문제은행. 세트 A·B(20문항 30분), 무작위, 단답형만, 전체. 보기 길이를 비슷하게 맞춰 길이로 정답을 고를 수 없게 했다 |
| 활용평가 모의고사 | 과제 4개 × 4문항. 지문·파일 목록(토큰량)·문항·AI 어시스트 화면 |
| 서술형 모의 | 2차 예선 대비 보고서 과제, 자가 채점표, 모범 개요 |
| 드릴 | AI 답변 검증 10문항, 프롬프트 판단 6문항 (보기 순서는 매번 섞임) |
| 정답·풀이 가이드 | 활용평가 과제별 회차 풀이: ‘문제’에서 고를 문항, 첨부할 파일과 토큰 합계, 프롬프트 전문(글자 수), AI가 줘야 할 정답 중간표, 확인할 것, 최종 답 검산. 지식평가 52문항 보기별 정오 이유와 지문 단서. 서술형 회차 풀이, 모범 보고서 전문, 채점 항목 대응표 |
| 치트시트·복기·오답노트 | 개념 33개와 오답 보기 문장, 넥슨 AI 역량평가 복기, 자동 오답노트 |

### 모의고사가 흉내 내는 시험 환경

- 프롬프트 입력 1,000자, 질문 1회 첨부 20,000토큰(파일별 토큰량은 추정치)
- AI 질문 10회를 1~4번 문항이 공유, 질문 뒤 30초 대기
- ‘문제’ 버튼으로 질문에 넣을 문항 선택, 파일은 ‘AI 질문에 추가’
- 지문·첨부 뷰어 복사 막기, 질문을 보내면 첨부가 비워짐
- 숫자는 모두 설정 화면에서 바꿀 수 있다

### AI 어시스트 연결 (선택)

설정 화면에서 OpenAI, Anthropic, Google Gemini 중 하나의 API 키와 모델 이름을 넣으면 모의고사 AI 어시스트가 실제 응답을 준다.
키는 브라우저 localStorage에만 저장되고 이 사이트 서버로는 가지 않는다. 키가 없으면 ‘연습 모드’로, 보낸 프롬프트를 점검해 주고 외부 AI에 붙여 넣을 수 있게 복사해 준다.

## 구조

```
index.html               앱 셸
assets/app.js            화면·채점·타이머·AI 어시스트 로직
assets/style.css         스타일 (라이트/다크)
assets/data/guide.js     가이드 본문, 템플릿, 치트시트, 체크리스트
assets/data/knowledge.js 지식평가 문제은행
assets/data/tasks.js     활용평가 과제 데이터와 정답 (자동 생성)
assets/data/drills.js    검증·프롬프트 드릴
assets/data/essay.js     서술형 과제
tools/gen_tasks.py       과제 데이터 생성 + 정답 계산
tools/verify_tasks.py    파일 텍스트만으로 정답을 다시 계산하는 검산
scripts/build-single.mjs 한 파일 버전(dist/) 만들기
server.js                의존성 없는 정적 서버
```

과제 데이터를 바꾸면:

```bash
npm run gen      # tasks.js 다시 만들고 정답 검산
npm run bundle   # dist/ 한 파일 버전 갱신
```

## 출처

- [SK하이닉스 AI 해커톤 2026 공고](https://skhynix-hackathon.com/ai-2026)
- [프로그래머스 AI 역량평가 응시 환경 체험](https://programmers.co.kr/ai-assessment/preview)
- [프로그래머스 AI 역량평가 소개서](https://programmers-ai.io/intro)
- [큰돌의터전: SK 하이닉스 해커톤 AI 활용능력 예상문제 만들어봄](https://www.youtube.com/watch?v=yeGeAYlIoZo)
- [벤처스퀘어: 그렙 AI 역량 평가 채점 기준](https://www.venturesquare.net/1116597/)
- [벤처스퀘어: 그렙 AI 역량평가 도입 현황](https://www.venturesquare.net/1119092)
- 문항별 근거 링크는 각 해설에 붙어 있다
