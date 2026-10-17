#!/usr/bin/env python3
"""활용평가 모의 과제 4개의 데이터 파일과 정답을 만든다.

정답은 손으로 적지 않고 이 스크립트가 규칙대로 계산한다.
실행: python3 tools/gen_tasks.py  ->  assets/data/tasks.js 생성
"""
import json
import math
import random
import datetime as dt
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "data" / "tasks.js"


def est_tokens(s: str) -> int:
    """앱(app.js)과 같은 공식으로 토큰을 추정한다. 실제 모델 토큰 수와는 다르다."""
    h = a = p = w = 0
    for ch in s:
        c = ord(ch)
        if 0xAC00 <= c <= 0xD7A3:
            h += 1
        elif ch.isascii() and ch.isalnum():
            a += 1
        elif ch.isspace():
            w += 1
        else:
            p += 1
    return math.ceil(h * 1.0 + a / 3.0 + p * 0.7 + w * 0.2)


def csv_text(header, rows):
    out = [",".join(header)]
    for r in rows:
        out.append(",".join(str(x) for x in r))
    return "\n".join(out) + "\n"


def round_half_up(x, nd=0):
    q = 10 ** nd
    return math.floor(x * q + 0.5) / q


# ---------------------------------------------------------------------------
# 과제 1. 팹 장비 알람 로그
# ---------------------------------------------------------------------------

def task1():
    R = random.Random(1017)
    equips = [
        ("ETCH-01", "식각", "A동 2라인", 720),
        ("ETCH-02", "식각", "A동 2라인", 720),
        ("ETCH-03", "식각", "A동 3라인", 696),
        ("ETCH-04", "식각", "A동 3라인", 720),
        ("CVD-01", "증착", "B동 1라인", 720),
        ("CVD-02", "증착", "B동 1라인", 600),
        ("CVD-03", "증착", "B동 2라인", 672),
        ("CMP-01", "평탄화", "B동 2라인", 720),
    ]
    planned = {e[0]: e[3] for e in equips}
    kind = {e[0]: e[0].split("-")[0] for e in equips}
    codes = {
        "A101": ("RF 반사파 과다", {"ETCH"}),
        "A107": ("챔버 압력 이탈", {"ETCH", "CVD"}),
        "A214": ("가스 유량 편차", {"CVD", "ETCH"}),
        "A230": ("히터 온도 이탈", {"CVD"}),
        "A305": ("웨이퍼 이송 오류", {"ETCH", "CVD", "CMP"}),
        "A412": ("슬러리 공급 압력 저하", {"CMP"}),
        "P900": ("계획 예방정비(PM)", {"ETCH", "CVD", "CMP"}),
    }

    def T(s):
        return dt.datetime.strptime(s, "%Y-%m-%d %H:%M")

    rows = []  # (time, equip, code, severity, downtime)

    # 심어 둔 패턴 ---------------------------------------------------------
    planted = [
        # 반복 알람 O: 23시간 20분 안에 3건
        ("2026-09-03 08:10", "ETCH-02", "A101", "Major", 35),
        ("2026-09-03 19:45", "ETCH-02", "A101", "Critical", 190),
        ("2026-09-04 07:30", "ETCH-02", "A101", "Major", 40),
        # 반복 알람 O: 첫 건과 셋째 건 간격이 정확히 24시간(포함)
        ("2026-09-12 01:00", "CVD-02", "A214", "Critical", 210),
        ("2026-09-12 13:00", "CVD-02", "A214", "Major", 55),
        ("2026-09-13 01:00", "CVD-02", "A214", "Major", 45),
        # 반복 알람 X: 24시간 30분 (근소하게 초과)
        ("2026-09-20 02:00", "ETCH-03", "A107", "Major", 30),
        ("2026-09-20 14:00", "ETCH-03", "A107", "Critical", 140),
        ("2026-09-21 02:30", "ETCH-03", "A107", "Major", 25),
        # 반복 알람 O: 23시간
        ("2026-09-25 10:00", "CVD-03", "A230", "Critical", 260),
        ("2026-09-25 18:00", "CVD-03", "A230", "Major", 50),
        ("2026-09-26 09:00", "CVD-03", "A230", "Minor", 5),
        # 같은 코드지만 장비가 모두 다름 -> 반복 알람 아님
        ("2026-09-16 09:20", "ETCH-01", "A305", "Minor", 6),
        ("2026-09-16 13:40", "CVD-01", "A305", "Minor", 8),
        ("2026-09-16 21:05", "CMP-01", "A305", "Major", 20),
        # 기간 밖 1건을 넣으면 3건이 되는 함정 (8/31은 집계 제외)
        ("2026-08-31 21:00", "CMP-01", "A412", "Major", 40),
        ("2026-09-01 06:00", "CMP-01", "A412", "Major", 35),
        ("2026-09-01 15:00", "CMP-01", "A412", "Critical", 150),
        # 기간 밖 Critical (10/1) -> 넣으면 CVD-02가 1위가 되는 함정
        ("2026-10-01 00:20", "CVD-02", "A107", "Critical", 480),
        ("2026-08-31 23:40", "ETCH-04", "A101", "Minor", 4),
        ("2026-10-01 02:10", "ETCH-01", "A214", "Major", 30),
    ]
    for t, e, c, s, d in planted:
        rows.append((T(t), e, c, s, d))

    # 장비별 Critical 다운타임 목표 합계 (심어 둔 Critical 포함)
    crit_target = {
        "ETCH-01": 275, "ETCH-02": 2310, "ETCH-03": 820, "ETCH-04": 410,
        "CVD-01": 655, "CVD-02": 2040, "CVD-03": 1380, "CMP-01": 1150,
    }
    # Major 다운타임은 CVD-02를 크게 만들어 'Major까지 더하면 순위가 바뀌는' 함정을 만든다
    major_target = {
        "ETCH-01": 180, "ETCH-02": 300, "ETCH-03": 260, "ETCH-04": 210,
        "CVD-01": 240, "CVD-02": 960, "CVD-03": 330, "CMP-01": 200,
    }

    def in_sept(t):
        return dt.datetime(2026, 9, 1) <= t <= dt.datetime(2026, 9, 30, 23, 59)

    def split_amount(total, n, lo, hi):
        """total을 n개로 나누되 각 값이 lo~hi 범위가 되게 한다."""
        for _ in range(10000):
            parts = [R.randint(lo, hi) for _ in range(n - 1)]
            last = total - sum(parts)
            if lo <= last <= hi:
                parts.append(last)
                R.shuffle(parts)
                return parts
        raise RuntimeError("split failed")

    # 이미 들어간 Critical/Major(9월분)를 빼고 남은 양을 새 알람으로 채운다
    for e, _, _, _ in equips:
        have_c = sum(d for t, ee, c, s, d in rows if ee == e and s == "Critical" and c != "P900" and in_sept(t))
        have_m = sum(d for t, ee, c, s, d in rows if ee == e and s == "Major" and c != "P900" and in_sept(t))
        rest_c = crit_target[e] - have_c
        rest_m = major_target[e] - have_m
        assert rest_c >= 0 and rest_m >= 0, (e, rest_c, rest_m)
        nc = max(1, round(rest_c / 210)) if rest_c else 0
        nm = max(1, round(rest_m / 40)) if rest_m else 0
        if nc:
            for d in split_amount(rest_c, nc, 60, 320) if nc > 1 else [rest_c]:
                rows.append((None, e, None, "Critical", d))
        if nm:
            for d in split_amount(rest_m, nm, 15, 70) if nm > 1 else [rest_m]:
                rows.append((None, e, None, "Major", d))
        # Minor 알람
        for _ in range(R.randint(6, 10)):
            rows.append((None, e, None, "Minor", R.randint(0, 12)))
        # 계획 예방정비 P900 (집계 제외 대상)
        rows.append((None, e, "P900", "Info", R.choice([240, 360, 480, 720, 1440])))

    # 시간과 코드가 비어 있는 행을 채운다. 같은 장비+코드는 13시간 넘게 띄워서 우연한 반복 알람을 막는다
    fixed = [r for r in rows if r[0] is not None]
    todo = [r for r in rows if r[0] is None]

    def ok(e, c, t, placed):
        for tt, ee, cc, _, _ in placed:
            if ee == e and cc == c and abs((tt - t).total_seconds()) < 13 * 3600:
                return False
        return True

    placed = list(fixed)
    for _, e, c, s, d in todo:
        for _ in range(5000):
            if c is None:
                cand = [k for k, (_, kinds) in codes.items() if k != "P900" and kind[e] in kinds]
                code = R.choice(cand)
            else:
                code = c
            day = R.randint(1, 30)
            t = dt.datetime(2026, 9, day, R.randint(0, 23), R.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]))
            if ok(e, code, t, placed):
                placed.append((t, e, code, s, d))
                break
        else:
            raise RuntimeError("placement failed")

    placed.sort(key=lambda r: (r[0], r[1]))

    # 정답 계산 ---------------------------------------------------------
    valid = [r for r in placed if in_sept(r[0]) and r[2] != "P900"]
    q1 = len(valid)

    crit = defaultdict(int)
    major = defaultdict(int)
    for t, e, c, s, d in valid:
        if s == "Critical":
            crit[e] += d
        if s == "Major":
            major[e] += d
    assert dict(crit) == crit_target, (dict(crit), crit_target)
    q2 = max(crit, key=lambda e: crit[e])

    by = defaultdict(list)
    for t, e, c, s, d in valid:
        by[(e, c)].append(t)
    rec = []
    for (e, c), ts in by.items():
        ts.sort()
        for i in range(len(ts) - 2):
            if ts[i + 2] - ts[i] <= dt.timedelta(hours=24):
                rec.append(f"{e}:{c}")
                break
    rec.sort()
    assert rec == ["CVD-02:A214", "CVD-03:A230", "ETCH-02:A101"], rec

    avail = {}
    for e in planned:
        pm = planned[e] * 60
        avail[e] = (pm - crit[e]) / pm * 100
    low = min(avail, key=lambda e: avail[e])
    q4 = round_half_up(avail[low], 1)
    assert low == "CVD-02"

    # 함정 확인용 값
    trap_all720 = {e: (43200 - crit[e]) / 43200 * 100 for e in planned}
    trap_low720 = min(trap_all720, key=lambda e: trap_all720[e])

    # 파일 ------------------------------------------------------------
    log_rows = []
    for i, (t, e, c, s, d) in enumerate(placed, 1):
        log_rows.append((f"L{i:04d}", t.strftime("%Y-%m-%d %H:%M"), e, c, s, d))
    f_log = csv_text(["log_id", "occurred_at", "equip_id", "alarm_code", "severity", "downtime_min"], log_rows)

    f_master = csv_text(
        ["equip_id", "공정", "위치", "planned_hours"],
        [(e, k, loc, h) for e, k, loc, h in equips],
    )
    code_lines = "\n".join(f"| {k} | {v[0]} |" for k, v in codes.items())
    f_rules = f"""# 9월 설비 알람 집계 기준 (설비기술팀)

## 1. 집계 기간
- 2026-09-01 00:00 부터 2026-09-30 23:59 까지 발생한 알람만 집계한다.
- 로그 파일에는 앞뒤 날짜의 알람이 일부 섞여 있을 수 있다.

## 2. 집계 제외
- 알람 코드 P900(계획 예방정비)은 알람 건수와 다운타임 집계에서 모두 제외한다.

## 3. 다운타임 손실
- 가동률 계산에 쓰는 다운타임은 severity가 Critical인 알람의 downtime_min만 합산한다.
- Major, Minor 알람의 downtime_min은 참고값이며 가동률에 반영하지 않는다.

## 4. 반복 알람 판정
- 같은 장비에서 같은 알람 코드가 3건 이상 발생하고, 그중 연속한 3건의 첫 건과 셋째 건 발생 시각 차이가 24시간 이내(24시간 정각 포함)이면 그 (장비, 코드) 조합을 반복 알람으로 판정한다.
- 장비가 다르면 같은 코드라도 반복 알람으로 묶지 않는다.

## 5. 가동률
- 가동률(%) = (계획 가동시간(분) - Critical 다운타임 합계(분)) / 계획 가동시간(분) × 100
- 계획 가동시간(분) = equipment_master.csv의 planned_hours × 60
- 결과는 소수점 둘째 자리에서 반올림해 첫째 자리까지 표기한다.

## 6. 알람 코드
| 코드 | 의미 |
|---|---|
{code_lines}
"""

    files = [
        {"name": "alarm_log_2026-09.csv", "kind": "csv", "text": f_log},
        {"name": "알람_집계_기준.md", "kind": "doc", "text": f_rules},
        {"name": "equipment_master.csv", "kind": "csv", "text": f_master},
    ]

    # 풀이 가이드 데이터 ------------------------------------------------
    lid = {}
    for i, r in enumerate(placed, 1):
        lid[(r[0], r[1], r[2])] = f"L{i:04d}"
    out_list = [(lid[(t, e, c)], t.strftime("%m/%d %H:%M"), e, c, s) for t, e, c, s, d in placed if not in_sept(t)]
    p900_in = [(lid[(t, e, c)], e) for t, e, c, s, d in placed if c == "P900" and in_sept(t)]
    crit_n = defaultdict(int)
    for t, e, c, s, d in valid:
        if s == "Critical":
            crit_n[e] += 1

    def hm(td):
        sec = int(td.total_seconds())
        return f"{sec // 3600}시간 {sec % 3600 // 60:02d}분"

    cand = []
    for (e, c), ts in by.items():
        ts = sorted(ts)
        best = None
        for i in range(len(ts) - 2):
            span = ts[i + 2] - ts[i]
            if best is None or span < best[0]:
                best = (span, ts[i], ts[i + 1], ts[i + 2])
        if best and best[0] <= dt.timedelta(hours=36):
            cand.append((e, c, best))
    cand.sort(key=lambda x: x[2][0])
    cand_rows = [[f"{e}:{c}", " → ".join(x.strftime("%m/%d %H:%M") for x in b[1:]), hm(b[0]),
                  "반복 알람" if b[0] <= dt.timedelta(hours=24) else "아님 (24시간 초과)"] for e, c, b in cand]
    order_e = [e for e, _, _, _ in equips]
    crit_rows = [[e, str(crit_n[e]), f"{crit[e]:,}"] for e in sorted(order_e, key=lambda x: -crit[x])]
    avail_rows = [[e, f"{planned[e]}", f"{planned[e] * 60:,}", f"{crit[e]:,}", f"{round_half_up(avail[e], 1):.1f}"]
                  for e in sorted(order_e, key=lambda x: avail[x])]
    t2_rows = []
    for e in ["CVD-02", "ETCH-02"]:
        rs = [(lid[(t, ee, c)], t.strftime("%m/%d %H:%M"), d) for t, ee, c, s, d in valid if ee == e and s == "Critical"]
        for r in rs:
            t2_rows.append([e, r[0], r[1], f"{r[2]}"])
        t2_rows.append([e, "합계", f"{len(rs)}건", f"{sum(r[2] for r in rs):,}"])

    t1_turn1 = (
        "[알람_집계_기준.md]의 규칙 1~5를 그대로 적용해 1~4번에 필요한 값을 한 번에 계산해줘.\n"
        "처리 순서: ①9/1 00:00~9/30 23:59만 남김 ②P900 제외 ③남은 건수 ④장비별 Critical downtime 합(Major·Minor 제외) "
        "⑤같은 장비+같은 코드의 연속 3건 간격이 24시간 이하인 조합(정각 포함) ⑥equipment_master의 planned_hours로 장비별 가동률.\n"
        "출력: 표 4개(①~③ 건수 내역 / 장비별 Critical 건수·합계 / 반복 알람 후보의 3건 시각·간격·판정 / 장비별 계획분·다운타임·가동률). "
        "기간 밖 행과 P900 행은 log_id를 적고, 판단이 애매한 행은 '확인 필요'로 따로 표시해. 추측으로 채우지 마."
    )
    t1_turn2 = (
        "CVD-02와 ETCH-02의 Critical 알람만 다시 확인해줘. 기간 9/1 00:00~9/30 23:59, P900 제외.\n"
        "장비별로 log_id, occurred_at, downtime_min을 시간순으로 나열하고, 장비마다 마지막 줄에 건수와 합계를 적어. 다른 장비는 계산하지 마."
    )
    walk = {
        "goal": "파일 3개 합계가 4,005토큰이라 한 번에 첨부된다. 첫 질문 한 번에 1~4번 값을 모두 받고, 숫자 두 개만 손으로 검산한다.",
        "reading": [
            {"q": "1번", "need": "9월 안 + P900 제외 후 건수", "src": "alarm_log, 알람_집계_기준 1·2"},
            {"q": "2번", "need": "장비별 Critical downtime 합 (Major·Minor 제외)", "src": "alarm_log, 기준 3"},
            {"q": "3번", "need": "같은 장비·같은 코드 연속 3건의 첫~셋째 간격 ≤ 24시간 (정각 포함)", "src": "alarm_log, 기준 4"},
            {"q": "4번", "need": "장비별 planned_hours로 가동률, 소수 첫째 자리", "src": "equipment_master, 기준 5"},
        ],
        "plan": "첨부 3개 전부(4,005토큰) → 1회차에 일괄 계산. 2회차는 숫자가 이상할 때만 쓴다. 나머지 8회는 남겨 둔다.",
        "turns": [
            {
                "n": 1, "title": "1~4번 값 일괄 계산",
                "select": [1, 2, 3, 4],
                "attach": ["alarm_log_2026-09.csv", "알람_집계_기준.md", "equipment_master.csv"],
                "prompt": t1_turn1,
                "why": "규칙 문서 번호를 그대로 부르고, 처리 순서를 박아서 기간·P900·severity 조건이 빠지지 않게 했다. 표 4개는 문항 4개와 1:1로 대응한다.",
                "expect": [
                    {"caption": "표 1. 건수 내역 (1번)", "headers": ["항목", "값"],
                     "rows": [["파일 전체 행", f"{len(placed)}"],
                              ["9월 밖 행", f"{len(out_list)}건 ({', '.join(x[0] for x in out_list)})"],
                              ["9월 안 P900 행", f"{len(p900_in)}건"],
                              ["남은 알람", f"{q1}건"]]},
                    {"caption": "표 2. 장비별 Critical (2번)", "headers": ["장비", "Critical 건수", "합계(분)"], "rows": crit_rows},
                    {"caption": "표 3. 반복 알람 후보 (3번, 최소 간격 36시간 이내만 표시)", "headers": ["장비:코드", "연속 3건 시각", "첫~셋째 간격", "판정"], "rows": cand_rows},
                    {"caption": "표 4. 가동률 (4번, 낮은 순)", "headers": ["장비", "계획(시간)", "계획(분)", "Critical(분)", "가동률(%)"], "rows": avail_rows},
                ],
                "checks": [
                    f"표 1의 전체 행이 {len(placed)}인지 본다. 뷰어 맨 아래 행 번호와 같아야 한다.",
                    f"9월 밖 {len(out_list)}건은 파일 맨 앞 2행(8/31)과 맨 뒤 2행(10/1)이다. 파일이 시간순이라 뷰어에서 바로 확인된다.",
                    "P900을 9월 안에서도 뺐는지 본다. 빼지 않으면 1번 값이 달라진다.",
                    "표 2에서 ETCH-02 2,310분, CVD-02 2,040분이 나오는지 본다. CVD-02가 더 크게 나오면 Major를 섞었거나 10/1 Critical 480분을 넣은 것이다.",
                    "표 3에서 CVD-02:A214 간격이 정확히 24시간이고 '반복 알람'으로 판정됐는지, ETCH-03:A107(24시간 30분)은 '아님'인지 본다.",
                    "CMP-01:A412는 9월 안에서는 어떤 연속 3건도 24시간 안에 들지 않는다. 9월 밖인 8/31 21:00 건을 넣었을 때만 3건이 18시간 안에 모인다. A305는 장비가 모두 달라 묶지 않는다.",
                    "표 4의 CVD-02 분모가 36,000분(600시간)인지 본다. 손 검산: (36,000 − 2,040) ÷ 36,000 = 0.94333 → 94.3%.",
                ],
            },
            {
                "n": 2, "title": "(선택) 다운타임 합계 재확인",
                "select": [2, 4],
                "attach": ["alarm_log_2026-09.csv"],
                "prompt": t1_turn2,
                "why": "1회차 표 2·4가 의심될 때만 쓴다. 범위를 장비 2대로 좁혀서, 어느 행이 들어가고 빠졌는지 직접 대조한다. 1회차 첨부는 질문 뒤 비워지므로 로그를 다시 붙인다.",
                "expect": [{"caption": "기대 결과", "headers": ["장비", "log_id", "발생 시각", "downtime(분)"], "rows": t2_rows}],
                "checks": ["두 장비의 합계가 2,040분, 2,310분과 같으면 1회차 값을 그대로 쓴다."],
            },
        ],
        "final": [
            {"q": "1번", "answer": f"{q1}", "how": f"{len(placed)}행 − 9월 밖 {len(out_list)} − 9월 안 P900 {len(p900_in)} = {q1}"},
            {"q": "2번", "answer": "① ETCH-02", "how": "Critical만 합산: ETCH-02 2,310분 > CVD-02 2,040분 > CVD-03 1,380분"},
            {"q": "3번", "answer": "① CVD-02:A214, CVD-03:A230, ETCH-02:A101", "how": "간격 24시간 이하 3개 조합. 24시간 정각은 포함, 24시간 30분은 제외"},
            {"q": "4번", "answer": f"{q4:.1f}", "how": "CVD-02: (36,000 − 2,040) ÷ 36,000 × 100 = 94.33 → 94.3"},
        ],
        "usage": "AI 1회(검산이 필요하면 2회) / 10회. 읽기 4분, 프롬프트 3분, 검증 6분, 입력 2분.",
    }

    eq_opts = ["ETCH-02", "CVD-02", "CMP-01", "CVD-03", "ETCH-03"]
    rec_opts = [
        "CVD-02:A214, CVD-03:A230, ETCH-02:A101",
        "CVD-03:A230, ETCH-02:A101",
        "CVD-02:A214, CVD-03:A230, ETCH-02:A101, ETCH-03:A107",
        "CMP-01:A412, CVD-02:A214, CVD-03:A230, ETCH-02:A101",
        "CVD-02:A214, CVD-03:A230, ETCH-02:A101, A305(장비 무관)",
    ]
    crit_lines = ", ".join(f"{e} {crit[e]:,}분" for e in sorted(crit, key=lambda x: -crit[x]))
    avail_lines = ", ".join(f"{e} {round_half_up(avail[e], 1)}%" for e in sorted(avail, key=lambda x: avail[x]))
    raw_in_file = len(placed)
    n_p900 = sum(1 for r in placed if r[2] == "P900")
    n_out = sum(1 for r in placed if not in_sept(r[0]))
    n_p900_in = sum(1 for r in placed if r[2] == "P900" and in_sept(r[0]))

    task = {
        "id": "T1",
        "title": "팹 장비 알람 로그 정리",
        "scenario": (
            "당신은 메모리 팹 설비기술팀 신입 엔지니어다. 팀장 보고 전에 9월 식각·증착·평탄화 장비 8대의 "
            "알람 로그를 정리해 수치를 확정해야 한다. 첨부한 로그와 집계 기준, 장비 마스터를 확인하고 아래 질문에 답하라."
        ),
        "cautions": [
            "집계 기준 문서의 규칙을 우선 적용한다.",
            "로그 파일에는 집계 기간 밖의 알람과 계획 예방정비 알람이 섞여 있다.",
        ],
        "files": files,
        "questions": [
            {
                "id": "T1Q1", "type": "short", "unit": "건",
                "prompt": "집계 기준을 적용했을 때 9월 알람은 모두 몇 건인가? (숫자만 입력)",
                "answer": str(q1), "numeric": True,
                "why": (
                    f"로그 파일 전체는 {raw_in_file}행이다. 여기서 9월이 아닌 {n_out}건과 9월 안의 P900 {n_p900_in}건을 빼면 {q1}건이다. "
                    "P900은 9월 안에 있어도 제외한다는 점을 AI가 자주 놓친다."
                ),
                "trap": "기간 밖 행 제외 + P900 제외를 둘 다 해야 한다. 하나만 하면 다른 숫자가 나온다.",
            },
            {
                "id": "T1Q2", "type": "mc",
                "prompt": "Critical 다운타임 합계가 가장 큰 장비는?",
                "options": eq_opts, "answer": eq_opts.index(q2),
                "why": (
                    f"9월·P900 제외·Critical만 합산하면 {crit_lines}. "
                    "Major까지 더하거나 10/1 Critical 480분을 넣으면 CVD-02가 1위로 바뀐다."
                ),
                "trap": "severity 조건, 기간 조건을 빠뜨리면 CVD-02를 고르게 된다.",
            },
            {
                "id": "T1Q3", "type": "mc",
                "prompt": "반복 알람으로 판정되는 (장비:코드) 조합을 빠짐없이 고른 것은?",
                "options": rec_opts, "answer": 0,
                "why": (
                    "ETCH-02:A101은 23시간 20분, CVD-03:A230은 23시간 안에 3건이다. CVD-02:A214는 정확히 24시간인데 기준이 '24시간 정각 포함'이라 반복 알람이다. "
                    "ETCH-03:A107은 24시간 30분이라 아니다. CMP-01:A412는 9월 밖인 8/31 21:00 건을 넣어야만 24시간 안에 3건이 된다. A305는 장비가 모두 달라 묶지 않는다."
                ),
                "trap": "경계값(정확히 24시간), 근소 초과(24시간 30분), 기간 밖 1건, 장비 다른 같은 코드. 네 가지 함정이 한 문항에 있다.",
            },
            {
                "id": "T1Q4", "type": "short", "unit": "%",
                "prompt": "가동률이 가장 낮은 장비의 가동률(%)은? (소수점 첫째 자리까지, 숫자만)",
                "answer": f"{q4:.1f}", "numeric": True, "decimals": 1,
                "why": (
                    f"장비별 가동률(낮은 순): {avail_lines}. CVD-02는 계획 가동시간이 600시간(36,000분)이라 다운타임이 ETCH-02보다 적어도 가동률이 더 낮다. "
                    f"모든 장비를 720시간으로 계산하면 {trap_low720}가 최저로 잘못 나온다."
                ),
                "trap": "장비별 planned_hours가 다르다. AI가 720시간으로 일괄 계산하는지 확인해야 한다.",
            },
        ],
        "promptExample": (
            "[알람_집계_기준.md]의 규칙 1~5를 그대로 적용해 1~4번에 필요한 값을 한 번에 계산해줘.\n"
            "처리 순서: ①9/1 00:00~9/30 23:59만 남김 ②P900 제외 ③남은 건수 ④장비별 Critical downtime 합(Major·Minor 제외) "
            "⑤같은 장비+같은 코드의 연속 3건 간격이 24시간 이하인 조합(정각 포함) ⑥equipment_master의 planned_hours로 장비별 가동률.\n"
            "출력: 표 3개(장비별 Critical 합 / 반복 알람 후보와 3건의 시각·간격 / 장비별 계획분·다운타임·가동률). "
            "각 값의 계산식과 근거 log_id를 적고, 판단이 애매한 행은 '확인 필요'로 따로 표시해. 추측으로 채우지 마."
        ),
        "lessons": [
            "규칙 문서를 첨부하고 '규칙 번호대로 적용'이라고 지시하면 조건 누락이 줄어든다.",
            "반복 알람처럼 경계값이 있는 판정은 3건의 시각과 간격을 표로 받아 직접 확인한다.",
            "가동률처럼 계산이 들어가는 값은 분자·분모를 따로 받아 내가 다시 나눈다.",
        ],
        "walk": walk,
        "meta": {"crit": dict(crit), "avail": {k: round(v, 4) for k, v in avail.items()}},
    }
    return task


# ---------------------------------------------------------------------------
# 과제 2. 사내 AI 교육 만족도 설문
# ---------------------------------------------------------------------------

def task2():
    R = random.Random(2026)
    depts = [("공정기술", 28), ("설계", 22), ("품질", 18), ("경영지원", 12), ("보안", 5)]

    def ts(day, h, m):
        return dt.datetime(2026, 9, day, h, m)

    people = []
    n = 0
    for d, cnt in depts:
        for _ in range(cnt):
            n += 1
            people.append({"id": f"S{n:03d}", "dept": d})

    # 부서별 점수 성향: 품질 > 설계 > 공정기술 > 경영지원. 보안은 인원은 적지만 점수가 가장 높다
    base = {"공정기술": 3.6, "설계": 3.9, "품질": 4.15, "경영지원": 3.4, "보안": 4.6}

    def likert(mu):
        v = round(R.gauss(mu, 0.55))
        return max(1, min(5, v))

    final = {}
    for p in people:
        mu = base[p["dept"]]
        sess = R.choice([0, 1, 2, 3, 4, 4, 3, 2])
        qs = [likert(mu + (sess - 2) * 0.12) for _ in range(5)]
        rec = max(0, min(10, round(R.gauss(mu * 2 - 0.6 + (sess - 2) * 0.3, 1.6))))
        final[p["id"]] = {"dept": p["dept"], "q": qs, "rec": rec, "sess": sess,
                          "t": ts(R.randint(14, 23), R.randint(8, 20), R.randint(0, 59))}

    # 결측·범위 밖 값 심기 (최종 응답 기준)
    ids = [p["id"] for p in people]
    R.shuffle(ids)
    # 유효 문항이 3개 미만이 되는 응답자 2명
    for sid in ids[:2]:
        q = final[sid]["q"]
        q[0] = ""
        q[2] = 6
        q[4] = ""
    # 1~2개 문항만 결측/범위 밖
    for sid in ids[2:9]:
        q = final[sid]["q"]
        q[R.randint(0, 4)] = R.choice(["", 0, 6])
    # 추천 점수 결측 3명
    for sid in ids[9:12]:
        final[sid]["rec"] = ""

    # 중복 제출: 5명은 2번, 1명은 3번. 앞선 제출은 점수를 낮게 만들어 '중복 미제거' 함정을 만든다
    dup2 = [i for i in ids[12:40] if final[i]["dept"] == "품질"][:4] + \
        [i for i in ids[12:60] if final[i]["dept"] == "공정기술"][:1]
    dup3 = [i for i in ids[12:70] if final[i]["dept"] == "품질" and i not in dup2][:1]
    earlier = []
    for sid in dup2 + dup3:
        k = 2 if sid in dup3 else 1
        for j in range(k):
            f = final[sid]
            early = {
                "dept": f["dept"],
                "q": [max(1, (x if isinstance(x, int) and 1 <= x <= 5 else 3) - 2) for x in f["q"]],
                "rec": 3 if f["rec"] != "" else "",
                "sess": f["sess"],
                "t": f["t"] - dt.timedelta(days=1 + j, hours=2),
            }
            earlier.append((sid, early))

    rows = []
    for sid in [p["id"] for p in people]:
        f = final[sid]
        rows.append((sid, f))
    for sid, e in earlier:
        rows.append((sid, e))
    R.shuffle(rows)
    # 3번 제출한 사람은 가장 늦은 제출이 파일 맨 뒤가 아니게 배치 (파일 순서로 고르면 틀린다)
    tri = dup3[0]
    tri_rows = [r for r in rows if r[0] == tri]
    tri_rows.sort(key=lambda r: r[1]["t"])
    latest = tri_rows[-1]
    rows = [r for r in rows if r[0] != tri]
    rows.append(tri_rows[0])
    rows.insert(30, latest)
    rows.append(tri_rows[1])

    header = ["resp_id", "submitted_at", "dept", "q1", "q2", "q3", "q4", "q5", "recommend", "sessions_attended"]
    out = []
    for sid, f in rows:
        out.append([sid, f["t"].strftime("%Y-%m-%d %H:%M"), f["dept"]] + f["q"] + [f["rec"], f["sess"]])
    f_raw = csv_text(header, out)

    # 정답 계산 ---------------------------------------------------------
    latest_by = {}
    for sid, f in rows:
        if sid not in latest_by or f["t"] > latest_by[sid]["t"]:
            latest_by[sid] = f
    q1 = len(latest_by)
    raw_n = len(rows)

    def valid_q(x):
        return isinstance(x, int) and 1 <= x <= 5

    sat = {}
    excluded = []
    for sid, f in latest_by.items():
        vals = [x for x in f["q"] if valid_q(x)]
        if len(vals) < 3:
            excluded.append(sid)
            continue
        sat[sid] = sum(vals) / len(vals)

    dept_n = defaultdict(int)
    for sid, f in latest_by.items():
        dept_n[f["dept"]] += 1
    dept_sat = {}
    for d, cnt in dept_n.items():
        vals = [sat[s] for s, f in latest_by.items() if f["dept"] == d and s in sat]
        dept_sat[d] = sum(vals) / len(vals)
    eligible = {d: v for d, v in dept_sat.items() if dept_n[d] >= 8}
    q3 = max(eligible, key=lambda d: eligible[d])

    recs = [f["rec"] for f in latest_by.values() if f["rec"] != ""]
    prom = sum(1 for r in recs if r >= 9)
    detr = sum(1 for r in recs if r <= 6)
    idx = (prom - detr) / len(recs) * 100
    q2 = int(round_half_up(idx, 0))

    # 함정: 중복 제거 없이 계산하면 1위가 바뀌는지 확인
    nodup_sat = defaultdict(list)
    for sid, f in rows:
        vals = [x for x in f["q"] if valid_q(x)]
        if len(vals) >= 3:
            nodup_sat[f["dept"]].append(sum(vals) / len(vals))
    nodup_rank = {d: sum(v) / len(v) for d, v in nodup_sat.items() if dept_n[d] >= 8}
    nodup_top = max(nodup_rank, key=lambda d: nodup_rank[d])

    # 출석 0회 vs 4회
    g = defaultdict(list)
    for sid, f in latest_by.items():
        if sid in sat:
            g[f["sess"]].append(sat[sid])
    s0 = sum(g[0]) / len(g[0])
    s4 = sum(g[4]) / len(g[4])

    f_rules = """# AI 활용 교육 만족도 설문 집계 기준 (인사팀)

1. 같은 resp_id가 여러 번 제출된 경우, submitted_at이 가장 늦은 응답 1건만 유효하다. 파일의 행 순서는 제출 순서와 다를 수 있다.
2. q1~q5는 1~5점 척도다. 값이 비어 있거나 1~5 범위를 벗어나면 그 문항만 결측으로 처리한다.
3. 응답자 만족도 = 그 응답자의 유효 문항(q1~q5) 점수 평균. 유효 문항이 3개 미만인 응답자는 만족도 계산에서 제외한다.
4. 부서 만족도 = 부서에 속한 응답자 만족도의 평균. 부서 간 비교는 유효 응답자(중복 제거 후) 8명 이상인 부서만 대상으로 한다.
5. 추천지수 = (recommend 9~10점 응답자 비율 - 0~6점 응답자 비율) × 100. recommend가 빈 응답자는 분모와 분자에서 모두 제외한다. 결과는 소수점 첫째 자리에서 반올림한 정수로 표기한다.
6. sessions_attended는 교육 출석 회차(0~4회)이며 참고 정보다.
"""
    files = [
        {"name": "survey_raw.csv", "kind": "csv", "text": f_raw},
        {"name": "설문_집계_기준.md", "kind": "doc", "text": f_rules},
    ]
    dept_lines = ", ".join(f"{d} {dept_sat[d]:.3f}점({dept_n[d]}명)" for d in sorted(dept_sat, key=lambda x: -dept_sat[x]))
    opts3 = ["공정기술", "설계", "품질", "경영지원", "보안"]
    assert q3 == "품질", (q3, dept_sat)
    assert nodup_top != q3, (nodup_top, nodup_rank)
    assert len(excluded) == 2
    assert raw_n - q1 == 7

    # 풀이 가이드 데이터 ------------------------------------------------
    pos = defaultdict(list)
    for i, (sid, f) in enumerate(rows, 1):
        pos[sid].append((i, f))
    dup_rows = []
    for sid in sorted(k for k, v in pos.items() if len(v) > 1):
        keep = max(pos[sid], key=lambda x: x[1]["t"])
        dup_rows.append([sid, f"{len(pos[sid])}번", ", ".join(f"{i}행" for i, _ in pos[sid]), f"{keep[0]}행 ({keep[1]['t'].strftime('%m/%d %H:%M')})"])
    excl_rows = []
    for sid in sorted(excluded):
        qv = latest_by[sid]["q"]
        excl_rows.append([sid, " / ".join(str(x) if x != "" else "빈칸" for x in qv), f"{sum(1 for x in qv if valid_q(x))}개"])
    dept_rows = [[d, f"{dept_n[d]}", f"{dept_sat[d]:.3f}", "비교 대상" if dept_n[d] >= 8 else "제외 (8명 미만)"] for d in sorted(dept_sat, key=lambda x: -dept_sat[x])]
    tri_rows = [[f"{i}행", f["t"].strftime("%Y-%m-%d %H:%M"), "남김" if (i, f) == max(pos[tri], key=lambda x: x[1]["t"]) else "버림"] for i, f in pos[tri]]
    t2_turn1 = (
        "[설문_집계_기준.md] 1~6을 순서대로 적용해 1~4번에 필요한 값을 한 번에 정리해줘.\n"
        "①resp_id별 submitted_at 최신 1건만 남기고, 2번 이상 제출한 ID 표(제출 수, 남긴 행)와 지운 행 수·남은 인원을 먼저 보고해. "
        "②q1~q5에서 빈칸·1~5 밖 값은 결측. 유효 문항 3개 미만 응답자 ID. "
        "③부서별 인원·부서 만족도 표(8명 미만 부서는 '비교 제외' 표시). "
        "④recommend 빈칸 제외 후 9~10점 수, 0~6점 수, 분모, 추천지수 계산식. "
        "⑤sessions_attended 0회·4회 응답자의 평균 만족도.\n"
        "기준에 없는 가정은 하지 마. 4번 보기 판단은 위 표의 숫자로만 해."
    )
    t2_turn2 = (
        f"resp_id {tri}의 제출 행을 모두 찾아 파일 행 번호, submitted_at과 함께 보여주고, 기준 1에 따라 남길 행을 표시해줘. "
        "파일 행 순서가 아니라 submitted_at으로 판단해."
    )
    walk = {
        "goal": "파일 2개 합계 2,145토큰. 1회차에 중복 정리부터 추천지수까지 한 번에 받고, 인원 수 두 개(85명, 2명)와 추천지수 식을 손으로 맞춘다.",
        "reading": [
            {"q": "1번", "need": "중복 제출 정리 후 인원 (최신 submitted_at 기준)", "src": "survey_raw, 기준 1"},
            {"q": "2번", "need": "recommend 빈칸 제외, (9~10점 비율 − 0~6점 비율) × 100", "src": "survey_raw, 기준 5"},
            {"q": "3번", "need": "부서 만족도, 8명 이상 부서만 비교", "src": "survey_raw, 기준 2~4"},
            {"q": "4번", "need": "보기 5개를 위 숫자로 판정 (인과·인원·결측 규칙)", "src": "1~3번 결과 + 기준 1·3·5"},
        ],
        "plan": "첨부 2개 전부(2,145토큰) → 1회차 일괄. 2회차는 3번 제출한 ID 처리를 확인할 때만.",
        "turns": [
            {
                "n": 1, "title": "중복 정리 → 결측 → 부서 → 추천지수 일괄",
                "select": [1, 2, 3, 4], "attach": ["survey_raw.csv", "설문_집계_기준.md"],
                "prompt": t2_turn1,
                "why": "중복 정리를 맨 앞에 두고 '지운 행 수와 남은 인원'을 먼저 보고하게 해서 검증 지점을 만들었다. 부서 표에 인원 열을 넣게 해야 8명 조건 누락이 바로 보인다.",
                "expect": [
                    {"caption": "중복 제출 정리 (1번)", "headers": ["resp_id", "제출 수", "파일 위치", "남길 행"], "rows": dup_rows},
                    {"caption": "인원 요약", "headers": ["항목", "값"], "rows": [["원자료 행", f"{raw_n}"], ["지운 행", f"{raw_n - q1}"], ["유효 응답자", f"{q1}명"], ["만족도 제외(유효 문항 3개 미만)", f"{len(excluded)}명"]]},
                    {"caption": "만족도 제외 응답자", "headers": ["resp_id", "q1~q5", "유효 문항"], "rows": excl_rows},
                    {"caption": "부서 만족도 (3번)", "headers": ["부서", "인원", "부서 만족도", "비교"], "rows": dept_rows},
                    {"caption": "추천지수 (2번)", "headers": ["recommend 있는 인원", "9~10점", "0~6점", "계산", "답"],
                     "rows": [[f"{len(recs)}", f"{prom}", f"{detr}", f"({prom} − {detr}) ÷ {len(recs)} × 100 = {idx:.2f}", f"{q2}"]]},
                    {"caption": "출석 회차별 평균 (4번 보기 판단용)", "headers": ["출석", "평균 만족도"], "rows": [["0회", f"{s0:.2f}"], ["4회", f"{s4:.2f}"]]},
                ],
                "checks": [
                    f"원자료 {raw_n}행 − 유효 {q1}명 = {raw_n - q1}행이다. 2번 이상 제출한 ID는 6개인데 지운 행은 7개다. 3번 낸 사람이 있기 때문이다.",
                    f"부서 인원 합이 {q1}명인지 더해 본다.",
                    "보안은 5명이라 '비교 제외'여야 한다. AI가 보안을 1위로 쓰면 기준 4를 놓친 것이다.",
                    "추천지수는 표의 세 숫자로 직접 다시 계산한다. 빈칸을 0점으로 넣었으면 분모가 달라진다.",
                    "4번: 출석 0회와 4회 평균 차이는 관련성일 뿐 인과가 아니다. '정확히 6명'은 7과 다르다. 빈칸 0점 처리는 기준 5와 반대다. 남는 보기가 정답이다.",
                ],
            },
            {
                "n": 2, "title": "(선택) 3번 제출한 ID 확인",
                "select": [1], "attach": ["survey_raw.csv"], "prompt": t2_turn2,
                "why": "파일 행 순서와 제출 시각 순서가 다르게 섞여 있다. AI가 '마지막 행'을 남겼는지 '최신 시각'을 남겼는지 한 번에 가려낸다.",
                "expect": [{"caption": f"{tri}의 제출 기록", "headers": ["위치", "submitted_at", "판정"], "rows": tri_rows}],
                "checks": ["남긴 행이 가장 늦은 시각인지 본다. 파일의 마지막 행이 아니어도 된다."],
            },
        ],
        "final": [
            {"q": "1번", "answer": f"{q1}", "how": f"{raw_n}행 − 중복 {raw_n - q1}행"},
            {"q": "2번", "answer": f"{q2}", "how": f"({prom} − {detr}) ÷ {len(recs)} × 100 = {idx:.2f} → 반올림"},
            {"q": "3번", "answer": f"③ {q3}", "how": "8명 이상 부서 중 최고. 보안(5명)은 제외"},
            {"q": "4번", "answer": "④ 유효 문항 3개 미만 응답자는 2명", "how": "나머지 보기는 인과 단정, 인원 조건 무시, 7을 6으로, 기준 5 반대"},
        ],
        "usage": "AI 1회(확인까지 2회) / 10회. 읽기 4분, 프롬프트 3분, 검증 7분, 입력 2분.",
    }

    opts4 = [
        "출석 4회 응답자의 평균 만족도가 0회 응답자보다 높으므로, 출석을 늘리면 만족도가 올라간다는 인과관계가 확인된다.",
        "보안팀의 부서 만족도가 가장 높으므로 보안팀 운영 방식을 다른 부서로 확산하는 것이 근거 있는 결론이다.",
        "중복 제출을 정리하면 유효 응답자 수는 원자료 행 수보다 정확히 6명 적다.",
        "유효 문항이 3개 미만이라 만족도 계산에서 빠지는 응답자는 2명이다.",
        "recommend가 비어 있는 응답자는 0점(비추천)으로 보고 추천지수 분모에 포함해야 한다.",
    ]
    task = {
        "id": "T2",
        "title": "AI 활용 교육 만족도 설문",
        "scenario": (
            "인사팀에서 전사 'AI 활용 교육' 만족도 설문 결과 보고를 맡았다. 원자료에는 중복 제출, 빈칸, 잘못 입력된 점수가 섞여 있다. "
            "집계 기준에 맞춰 수치를 정리하고 아래 질문에 답하라."
        ),
        "cautions": ["집계 기준 1~6을 모두 적용한다.", "부서 비교는 기준 4의 인원 조건을 지킨다."],
        "files": files,
        "questions": [
            {
                "id": "T2Q1", "type": "short", "unit": "명",
                "prompt": "중복 제출을 정리한 뒤 유효 응답자는 몇 명인가? (숫자만)",
                "answer": str(q1), "numeric": True,
                "why": f"원자료 {raw_n}행 중 중복 제출 7행(2번 제출 5명 + 3번 제출 1명)을 빼면 {q1}명이다.",
                "trap": "3번 제출한 사람이 있어서 '중복된 ID 수'만큼 빼면 틀린다.",
            },
            {
                "id": "T2Q2", "type": "short", "unit": "",
                "prompt": "추천지수는? (정수, 숫자만. 음수면 - 부호 포함)",
                "answer": str(q2), "numeric": True,
                "why": f"recommend가 있는 유효 응답자 {len(recs)}명 중 9~10점 {prom}명, 0~6점 {detr}명. ({prom}-{detr})/{len(recs)}×100 = {idx:.2f} → {q2}.",
                "trap": "빈 값을 0점으로 넣거나, 중복 제출을 남겨 두면 값이 달라진다.",
            },
            {
                "id": "T2Q3", "type": "mc",
                "prompt": "부서 비교 대상 중 부서 만족도가 가장 높은 부서는?",
                "options": opts3, "answer": opts3.index(q3),
                "why": (
                    f"부서 만족도: {dept_lines}. 보안은 5명이라 비교 대상이 아니다. "
                    f"중복 제출을 지우지 않고 계산하면 앞선 낮은 점수가 섞여 {nodup_top}이 1위로 바뀐다."
                ),
                "trap": "인원 조건(8명 이상)과 중복 제거, 두 함정이 겹쳐 있다.",
            },
            {
                "id": "T2Q4", "type": "mc",
                "prompt": "다음 중 집계 기준과 데이터로 뒷받침되는 설명은?",
                "options": opts4, "answer": 3,
                "why": (
                    f"유효 문항 3개 미만 응답자는 {len(excluded)}명이다. 출석 0회 평균 {s0:.2f}, 4회 평균 {s4:.2f}로 차이는 있지만 설문 자료만으로 인과를 말할 수 없다. "
                    f"원자료 행 수와 유효 응답자 수의 차이는 {raw_n - q1}명이다. recommend 빈칸은 기준 5에 따라 제외한다."
                ),
                "trap": "상관을 인과로 읽는 보기, 규칙과 반대로 처리하는 보기는 AI가 그럴듯하게 동의해 주기 쉽다.",
            },
        ],
        "promptExample": (
            "[설문_집계_기준.md] 1~6을 순서대로 적용해 1~4번에 필요한 값을 한 번에 정리해줘.\n"
            "먼저 ①resp_id별 submitted_at 최신 1건만 남기고, 제거한 행 수와 남은 인원을 보고해. "
            "②q1~q5에서 빈칸·1~5 밖 값은 결측. 유효 문항 3개 미만 응답자 ID 목록. "
            "③부서별 인원·부서 만족도 표(8명 미만 부서는 '비교 제외' 표시). "
            "④recommend 빈칸 제외 후 9~10점 수, 0~6점 수, 분모, 추천지수 계산식.\n"
            "각 표에 근거가 된 resp_id를 남기고, 기준에 없는 가정은 하지 마. 4번 보기 판단은 위 표의 숫자로만 해."
        ),
        "lessons": [
            "중복 제거는 '어떤 기준으로 몇 행을 지웠는지'를 먼저 보고하게 하면 검증이 쉽다.",
            "인원 조건이 있는 비교는 표에 인원 열을 꼭 넣게 한다.",
            "해석형 보기는 숫자 근거가 있는지, 상관을 인과로 말하는지 본다.",
        ],
        "walk": walk,
        "meta": {"dept_sat": dept_sat, "nodup_rank": nodup_rank, "idx": idx, "s0": s0, "s4": s4},
    }
    return task


# ---------------------------------------------------------------------------
# 과제 3. 동호회 활동비 정산 (파일이 많아 토큰 한도를 넘는 과제)
# ---------------------------------------------------------------------------

def task3():
    R = random.Random(3033)
    clubs = ["등산", "러닝", "보드게임", "사진", "독서", "풋살", "요리", "밴드", "볼링"]
    surnames = list("김이박최정강조윤장임한오서신권황안송류홍")
    given = ["민준", "서연", "도윤", "지우", "하준", "서윤", "시우", "하은", "주원", "지민", "예준", "수아",
             "지호", "채원", "건우", "다은", "현우", "유진", "우진", "소율", "선우", "예린", "연우", "가은"]
    depts = ["공정기술팀", "설계팀", "품질팀", "구매팀", "인사팀", "재무팀", "생산관리팀", "IT운영팀", "안전환경팀"]
    stores = {
        "식비": ["산들식당", "한우마을", "바다횟집", "김밥천국 역점", "소문난국밥", "들깨칼국수", "버거하우스"],
        "대관료": ["시민체육관", "스튜디오 연", "합주실 소리터", "볼링센터 스트라이크", "풋살파크 A구장"],
        "물품": ["스포츠마트", "다이소 본점", "보드게임카페 주사위", "카메라샵 렌즈", "서점 책방길"],
        "교통": ["한빛관광버스", "카카오T", "코레일"],
        "주류": ["와인앤모어", "동네 편의점(주류)", "맥주창고"],
        "상품권": ["문화상품권 판매처"],
    }
    memos = {
        "식비": ["정기 모임 후 식사, 참석 {n}명, 회비 정산 전 선결제", "월례 활동 뒤풀이 식사 {n}명, 총무 카드 결제", "신입 환영 식사 {n}명 참석, 다음 모임 일정 공유"],
        "대관료": ["정기 활동 장소 대관 2시간, 사전 예약분", "합동 연습 공간 대여, 장비 포함 요금", "월례 대회 장소 사용료, 현장 결제"],
        "물품": ["활동 소모품 구입, 공용 보관함 비치", "공용 장비 보충, 파손분 교체", "모임 진행용 물품, 다음 분기까지 사용"],
        "교통": ["단체 이동 차량, 왕복 요금", "원거리 활동 이동비, 참석자 공동 이용"],
        "주류": ["뒤풀이 음료 구입", "행사용 음료"],
        "상품권": ["우수 참여자 시상용"],
    }

    period_start, period_end = dt.date(2026, 7, 1), dt.date(2026, 9, 30)
    rno = [1000]

    def next_no():
        rno[0] += R.randint(3, 17)
        return f"R-{rno[0]}"

    data = {}
    used_ids = set()

    def new_member_id():
        while True:
            m = f"E{R.randint(1000, 4999)}"
            if m not in used_ids:
                used_ids.add(m)
                return m

    for c in clubs:
        members = []
        for _ in range(R.randint(34, 40)):
            mid = new_member_id()
            name = R.choice(surnames) + R.choice(given)
            joined = dt.date(2025, R.randint(1, 12), R.randint(1, 28))
            members.append({"id": mid, "name": name, "dept": R.choice(depts),
                            "pos": R.choice(["사원", "선임", "책임", "수석"]),
                            "status": "재직", "leave": "", "joined": joined})
        data[c] = {"members": members, "receipts": []}

    def add(c, date, mid, cat, amount, store=None, memo=None, no=None):
        store = store or R.choice(stores[cat])
        memo = memo or R.choice(memos[cat]).format(n=R.randint(4, 12))
        item = {"식비": "식대", "대관료": "장소 대관", "물품": "소모품", "교통": "차량 이용", "주류": "주류", "상품권": "상품권"}[cat]
        rec = {"no": no or next_no(), "date": date, "mid": mid, "store": store, "item": item,
               "cat": cat, "amount": amount, "memo": memo}
        data[c]["receipts"].append(rec)
        return rec

    def rand_date():
        return period_start + dt.timedelta(days=R.randint(0, (period_end - period_start).days))

    # 심어 둔 사례 ----------------------------------------------------------
    # 가입 30일 미만 (위반) / 정확히 30일 (인정)
    m = data["러닝"]["members"][0]; m["joined"] = dt.date(2026, 8, 20)
    add("러닝", dt.date(2026, 9, 10), m["id"], "식비", 32000)              # 21일 -> 위반
    m = data["사진"]["members"][1]; m["joined"] = dt.date(2026, 7, 1)
    add("사진", dt.date(2026, 7, 31), m["id"], "물품", 27500)              # 30일 -> 인정
    m2 = data["사진"]["members"][2]; m2["joined"] = dt.date(2026, 7, 1)
    add("사진", dt.date(2026, 7, 30), m2["id"], "식비", 41000)             # 29일 -> 위반
    m = data["독서"]["members"][3]; m["joined"] = dt.date(2026, 9, 1)
    add("독서", dt.date(2026, 9, 18), m["id"], "물품", 19800)              # 17일 -> 위반
    m = data["볼링"]["members"][4]; m["joined"] = dt.date(2026, 8, 25)
    add("볼링", dt.date(2026, 9, 5), m["id"], "주류", 38000)               # 11일 + 주류 -> 두 사유
    m = data["요리"]["members"][5]; m["joined"] = dt.date(2026, 9, 3)
    add("요리", dt.date(2026, 9, 26), m["id"], "식비", 45500)              # 23일 -> 위반

    # 기간 밖
    add("등산", dt.date(2026, 6, 28), data["등산"]["members"][2]["id"], "교통", 48000)
    add("보드게임", dt.date(2026, 10, 2), data["보드게임"]["members"][1]["id"], "물품", 23000)

    # 주류·상품권
    add("밴드", dt.date(2026, 8, 14), data["밴드"]["members"][3]["id"], "주류", 27000)
    add("러닝", dt.date(2026, 7, 19), data["러닝"]["members"][4]["id"], "주류", 15600)
    add("독서", dt.date(2026, 9, 9), data["독서"]["members"][5]["id"], "상품권", 50000)

    # 퇴사자: 퇴사일 이후 사용(위반), 퇴사일 당일 사용(인정)
    m = data["요리"]["members"][6]; m["status"] = "퇴사"; m["leave"] = dt.date(2026, 8, 31)
    add("요리", dt.date(2026, 9, 4), m["id"], "식비", 36000)
    m = data["풋살"]["members"][6]; m["status"] = "퇴사"; m["leave"] = dt.date(2026, 9, 15)
    add("풋살", dt.date(2026, 9, 15), m["id"], "대관료", 44000)

    # 중복 청구: 동호회 사이(등산·풋살)와 같은 동호회 안(요리)
    dup_a = add("등산", dt.date(2026, 8, 22), data["등산"]["members"][7]["id"], "식비", 39000)
    add("풋살", dt.date(2026, 8, 22), data["풋살"]["members"][7]["id"], "식비", 39000, store=dup_a["store"], no=dup_a["no"])
    dup_b = add("요리", dt.date(2026, 7, 11), data["요리"]["members"][8]["id"], "물품", 28700)
    add("요리", dt.date(2026, 7, 11), data["요리"]["members"][8]["id"], "물품", 28700, store=dup_b["store"], no=dup_b["no"])

    # 건당 5만원 초과 (부분 인정). 풋살·밴드는 공고문(6만원)과 규정(5만원)의 차이가 결과를 바꾸게 설계
    add("등산", dt.date(2026, 7, 12), data["등산"]["members"][1]["id"], "교통", 86000)
    add("등산", dt.date(2026, 9, 6), data["등산"]["members"][3]["id"], "식비", 64000)
    add("풋살", dt.date(2026, 7, 25), data["풋살"]["members"][2]["id"], "대관료", 58000)
    add("풋살", dt.date(2026, 9, 12), data["풋살"]["members"][3]["id"], "대관료", 60000)
    add("밴드", dt.date(2026, 7, 8), data["밴드"]["members"][1]["id"], "대관료", 70000)
    add("밴드", dt.date(2026, 9, 20), data["밴드"]["members"][2]["id"], "대관료", 75000)
    add("볼링", dt.date(2026, 8, 9), data["볼링"]["members"][2]["id"], "대관료", 52000)

    # 규칙 적용 함수 ------------------------------------------------------
    member_index = {}
    for c in clubs:
        for m in data[c]["members"]:
            member_index[(c, m["id"])] = m

    def evaluate(cap_per_receipt=50000, use_cap=True):
        counts = defaultdict(int)
        for c in clubs:
            for r in data[c]["receipts"]:
                counts[r["no"]] += 1
        result = {}
        reasons = defaultdict(list)
        for c in clubs:
            total = 0
            for r in data[c]["receipts"]:
                m = member_index[(c, r["mid"])]
                rs = []
                if not (period_start <= r["date"] <= period_end):
                    rs.append("기간 밖")
                if (r["date"] - m["joined"]).days < 30:
                    rs.append("가입 30일 미만")
                if m["status"] == "퇴사" and m["leave"] and r["date"] > m["leave"]:
                    rs.append("퇴사 후 사용")
                if r["cat"] in ("주류", "상품권"):
                    rs.append("불인정 품목")
                if counts[r["no"]] >= 2:
                    rs.append("중복 청구")
                if rs:
                    reasons[r["no"]].extend(rs)
                    continue
                amt = min(r["amount"], cap_per_receipt) if use_cap else r["amount"]
                total += amt
            result[c] = total
        return result, reasons

    # 일반 영수증으로 목표 합계 맞추기 ---------------------------------------
    targets = {"등산": 352400, "러닝": 214600, "보드게임": 188300, "사진": 236900, "독서": 167200,
               "풋살": 287300, "요리": 241800, "밴드": 271000, "볼링": 198500}

    # 일반(유효) 영수증을 넣을 수 있는 회원: 가입 오래됐고 재직 중
    def eligible_members(c):
        return [m for m in data[c]["members"] if m["status"] == "재직" and m["joined"] <= dt.date(2026, 5, 1)]

    for c in clubs:
        cur, _ = evaluate()
        need = targets[c] - cur[c]
        assert need > 0, (c, need)
        # 8,000~46,000원 사이 금액으로 need를 채운다 (마지막 한 건은 정확히 맞춤)
        pool = eligible_members(c)
        while need > 0:
            if need <= 9000:
                amt = need
                if amt < 2000:
                    # 직전 영수증을 늘려서 흡수
                    last = [r for r in data[c]["receipts"] if r["cat"] in ("식비", "물품") and r["amount"] + amt <= 46000][-1]
                    last["amount"] += amt
                    need = 0
                    break
            else:
                amt = R.randrange(2000, 9000, 100)
                if need - amt < 2000:
                    amt = need - 2000
            cat = R.choice(["식비", "식비", "물품", "대관료", "교통"])
            add(c, rand_date(), R.choice(pool)["id"], cat, amt)
            need -= amt

    final50, reasons = evaluate(50000)
    final60, _ = evaluate(60000)
    nocap, _ = evaluate(10 ** 9, use_cap=False)
    assert final50 == targets, (final50, targets)
    over50 = sorted([c for c in clubs if final50[c] > 300000])
    over60 = sorted([c for c in clubs if final60[c] > 300000])
    overno = sorted([c for c in clubs if nocap[c] > 300000])
    assert over50 == ["등산"], over50
    assert set(over60) == {"등산", "풋살"}, over60
    assert set(overno) == {"등산", "풋살", "밴드"}, overno

    paid = {c: min(v, 300000) for c, v in final50.items()}
    total_paid = sum(paid.values())
    disallowed = sorted(reasons.keys())
    young = 0
    for c in clubs:
        for r in data[c]["receipts"]:
            m = member_index[(c, r["mid"])]
            if (r["date"] - m["joined"]).days < 30:
                young += 1

    # 파일 만들기 -------------------------------------------------------
    files = []
    for c in clubs:
        rec_rows = sorted(data[c]["receipts"], key=lambda r: (r["date"], r["no"]))
        f_rec = csv_text(["receipt_no", "use_date", "member_id", "가맹점", "품목", "category", "amount", "메모"],
                         [(r["no"], r["date"].isoformat(), r["mid"], r["store"], r["item"], r["cat"], r["amount"], r["memo"]) for r in rec_rows])
        f_mem = csv_text(["member_id", "이름", "소속", "직급", "재직상태", "퇴사일"],
                         [(m["id"], m["name"], m["dept"], m["pos"], m["status"], m["leave"].isoformat() if m["leave"] else "") for m in data[c]["members"]])
        f_join = csv_text(["member_id", "동호회", "가입일"],
                          [(m["id"], c, m["joined"].isoformat()) for m in data[c]["members"]])
        files.append({"name": f"{c}/영수증.csv", "kind": "csv", "text": f_rec})
        files.append({"name": f"{c}/회원명단.csv", "kind": "csv", "text": f_mem})
        files.append({"name": f"{c}/가입일.csv", "kind": "csv", "text": f_join})

    f_rules = """# 사내 동호회 활동비 정산 규정 (2026년 3분기)

제1조(목적) 이 규정은 사내 동호회 활동비 지원금의 정산 기준을 정한다.

제2조(대상 기간) 2026년 7월 1일부터 2026년 9월 30일까지 사용한 영수증만 정산한다. 사용일(use_date)을 기준으로 한다.

제3조(지원 대상자)
1. 영수증 사용자는 사용일 기준으로 해당 동호회 가입일로부터 30일 이상 지난 회원이어야 한다. (사용일 - 가입일 ≥ 30일)
2. 사용일에 재직 중이어야 한다. 퇴사일 이후 사용분은 인정하지 않으며, 퇴사일 당일 사용분은 인정한다.

제4조(불인정 품목) category가 주류 또는 상품권인 영수증은 인정하지 않는다.

제5조(건당 한도) 영수증 1건당 50,000원까지 인정한다. 초과분만 인정하지 않으며 영수증 자체는 유효하다.

제6조(중복 청구) 같은 영수증 번호(receipt_no)가 2회 이상 청구되면, 동호회가 달라도 그 번호의 청구를 모두 인정하지 않는다.

제7조(동호회별 한도) 동호회별 분기 지원 한도는 300,000원이다. 인정 금액 합계가 한도를 넘으면 300,000원만 지급한다.

제8조(우선 적용) 공고문과 이 규정의 내용이 다르면 이 규정을 따른다.
"""
    f_notice = """# [공고] 2026년 3분기 동호회 활동비 정산 신청 안내

- 신청 기간: 2026년 10월 1일 ~ 10월 10일
- 제출 방법: 동호회별 폴더에 영수증, 회원명단, 가입일 파일을 올린다.
- 지원 내용: 영수증 1건당 최대 60,000원, 동호회별 분기 최대 30만 원 지원
- 지급 예정일: 2026년 10월 24일 (급여 계좌 아님, 동호회 공용 계좌로 지급)
- 문의: 인사팀 복리후생 담당

※ 세부 기준은 '사내 동호회 활동비 정산 규정'을 따릅니다.
"""
    files.insert(0, {"name": "공고문.md", "kind": "doc", "text": f_notice})
    files.insert(0, {"name": "정산규정.md", "kind": "doc", "text": f_rules})

    total_tokens = sum(est_tokens(f["text"]) for f in files)

    # 풀이 가이드 데이터 ------------------------------------------------
    tok = {f["name"]: est_tokens(f["text"]) for f in files}
    rec_files = [f"{c}/영수증.csv" for c in clubs]
    rec_tok = sum(tok[n] for n in rec_files)
    assert rec_tok <= 20000, rec_tok
    where = defaultdict(list)
    for c in clubs:
        for r in data[c]["receipts"]:
            where[r["no"]].append(c)
    dup_list = sorted(no for no, cs in where.items() if len(cs) >= 2)

    def where_txt(no):
        cs = where[no]
        return ", ".join(f"{c} {cs.count(c)}건" if cs.count(c) > 1 else c for c in dict.fromkeys(cs))

    t3_dup_rows = [[no, where_txt(no)] for no in dup_list]
    t3_cat_rows = sorted([[r["no"], c, r["cat"]] for c in clubs for r in data[c]["receipts"] if r["cat"] in ("주류", "상품권")])
    t3_out_rows = sorted([[r["no"], c, r["date"].isoformat()] for c in clubs for r in data[c]["receipts"] if not (period_start <= r["date"] <= period_end)])
    t3_big_rows = sorted([[r["no"], c, f"{r['amount']:,}"] for c in clubs for r in data[c]["receipts"] if r["amount"] > 50000])

    detail = {}
    young_rows = []
    for c in clubs:
        bad, part, total = {}, [], 0
        for r in sorted(data[c]["receipts"], key=lambda x: x["no"]):
            m = member_index[(c, r["mid"])]
            rs = []
            if not (period_start <= r["date"] <= period_end):
                rs.append("기간 밖")
            days = (r["date"] - m["joined"]).days
            if days < 30:
                rs.append(f"가입 {days}일")
                young_rows.append([r["no"], c, r["date"].isoformat(), m["joined"].isoformat(), f"{days}일"])
            if m["status"] == "퇴사" and m["leave"] and r["date"] > m["leave"]:
                rs.append("퇴사 후")
            if r["cat"] in ("주류", "상품권"):
                rs.append(r["cat"])
            if len(where[r["no"]]) >= 2:
                rs.append("중복")
            if rs:
                bad.setdefault(r["no"], set()).update(rs)
                continue
            amt = min(r["amount"], 50000)
            if r["amount"] > 50000:
                part.append((r["no"], r["amount"], amt))
            total += amt
        detail[c] = (bad, part, total, min(total, 300000))
    assert {c: detail[c][2] for c in clubs} == final50
    young_rows.sort()

    batches = [clubs[0:3], clubs[3:6], clubs[6:9]]
    batch_files = [[f"{c}/{k}.csv" for c in b for k in ("영수증", "회원명단", "가입일")] for b in batches]
    batch_tok = [sum(tok[n] for n in bf) for bf in batch_files]
    assert all(t <= 20000 for t in batch_tok)

    def club_row(c):
        bad, part, total, paid_c = detail[c]
        return [c,
                ", ".join(f"{no}({'/'.join(sorted(rs))})" for no, rs in sorted(bad.items())) or "없음",
                ", ".join(f"{no} {a:,}→{b:,}" for no, a, b in part) or "없음",
                f"{total:,}", f"{paid_c:,}"]

    t3_turn1 = (
        "첨부한 정산규정과 공고문으로 영수증 판정표를 만들어줘. 다음 질문부터 내가 직접 옮겨 적을 거라 7줄 이내 번호 목록으로 짧게.\n"
        "각 줄: 조건 / 확인할 파일·열 / 경계값 처리 / 근거 조항.\n"
        "공고와 규정이 다른 항목은 무엇을 적용하는지 근거 조항과 함께 한 줄로 따로 적어줘. 문서에 없는 기준은 만들지 마."
    )
    t3_turn2 = (
        "첨부한 동호회 9곳 영수증.csv 전체에서 아래 네 가지만 찾아줘. 다른 판정은 하지 마.\n"
        "①receipt_no가 2번 이상 나온 번호와 나온 동호회 ②category가 주류·상품권인 영수증 ③use_date가 2026-07-01~2026-09-30 밖인 영수증 "
        "④amount가 50,000원을 넘는 영수증과 금액.\n항목마다 번호를 오름차순으로 생략 없이 적고 개수를 함께 써."
    )

    def batch_prompt(b):
        return (
            f"판정표: ①use_date 7/1~9/30만 ②use_date-가입일≥30일(member_id로 가입일.csv 연결) ③퇴사일 이후 불인정, 당일 인정 "
            f"④주류·상품권 불인정 ⑤중복 청구 {', '.join(dup_list)} 불인정 ⑥건당 5만 원 초과분만 불인정 ⑦동호회 한도 30만 원\n"
            f"첨부한 {'·'.join(b)} 동호회 파일에 적용해 동호회별로 알려줘: 전액 불인정 번호와 사유, 일부 인정 번호와 인정액, 인정 합계, 한도 적용 후 지급액. "
            "번호는 생략하지 말고, 이름으로 같은 사람을 추정하지 마."
        )

    rule_rows = [
        ["1", "사용 기간 2026-07-01~09-30", "영수증 use_date", "양 끝 날짜 포함", "제2조"],
        ["2", "가입 후 30일 이상", "영수증 use_date − 가입일.csv 가입일 (member_id로 연결)", "정확히 30일이면 인정", "제3조 1항"],
        ["3", "사용일에 재직", "회원명단 재직상태·퇴사일", "퇴사일 당일 사용은 인정", "제3조 2항"],
        ["4", "주류·상품권 불인정", "영수증 category", "-", "제4조"],
        ["5", "건당 50,000원까지", "영수증 amount", "초과분만 빼고 영수증은 유효", "제5조"],
        ["6", "같은 번호 2회 이상이면 전부 불인정", "모든 동호회의 receipt_no", "동호회가 달라도 적용", "제6조"],
        ["7", "동호회 한도 300,000원", "인정 합계", "넘으면 300,000원 지급", "제7조"],
        ["충돌", "공고 '건당 6만 원' vs 규정 '건당 5만 원'", "-", "규정의 5만 원 적용", "제8조"],
    ]
    turns3 = [
        {
            "n": 1, "title": "규정·공고로 판정표 만들기",
            "select": [1, 2, 3, 4], "attach": ["정산규정.md", "공고문.md"],
            "prompt": t3_turn1,
            "why": "데이터를 붙이기 전에 기준부터 고정한다. 판정표는 다음 질문마다 내가 직접 쳐서 넣어야 하니 짧게 받는다. 공고와 규정의 충돌을 이 단계에서 정리한다.",
            "expect": [{"caption": "기대 판정표", "headers": ["번호", "조건", "확인할 곳", "경계값", "근거"], "rows": rule_rows}],
            "checks": ["‘충돌’ 줄이 있는지 본다. 없으면 공고의 6만 원을 쓰게 되어 3번 문항이 틀린다.",
                       "규정에 없는 예외(예: 동호회장 승인)를 지어냈는지 본다."],
        },
        {
            "n": 2, "title": "영수증 9개만 붙여 전체 대조",
            "select": [1, 2, 3, 4], "attach": rec_files,
            "prompt": t3_turn2,
            "why": f"영수증 파일 9개만 합치면 {rec_tok:,}토큰이라 한 번에 들어간다. 중복 번호처럼 동호회 사이에 걸친 조건은 여기서만 잡을 수 있다. 회원명단·가입일이 필요 없는 규칙만 묻는다.",
            "expect": [
                {"caption": "① 중복 청구", "headers": ["receipt_no", "나온 곳"], "rows": t3_dup_rows},
                {"caption": "② 주류·상품권", "headers": ["receipt_no", "동호회", "category"], "rows": t3_cat_rows},
                {"caption": "③ 기간 밖", "headers": ["receipt_no", "동호회", "use_date"], "rows": t3_out_rows},
                {"caption": "④ 5만 원 초과 (부분 인정 후보)", "headers": ["receipt_no", "동호회", "amount"], "rows": t3_big_rows},
            ],
            "checks": [f"중복 번호 {len(dup_list)}개 중 하나는 등산·풋살 두 동호회에 걸쳐 있다. 동호회별로 따로 처리했다면 놓쳤을 번호다.",
                       "5만 원 초과 영수증은 ‘불인정’이 아니라 ‘일부 인정’이다. 다음 단계에서 5만 원만 인정한다."],
        },
    ]
    for bi, b in enumerate(batches):
        turns3.append({
            "n": 3 + bi, "title": f"묶음 {bi + 1}: {'·'.join(b)}",
            "select": [1, 2, 3, 4], "attach": batch_files[bi],
            "prompt": batch_prompt(b),
            "why": ("판정표를 직접 입력하고, 2회차에서 찾은 중복 번호를 ⑤에 넣었다. 동호회 3곳 파일 9개는 "
                    f"{batch_tok[bi]:,}토큰이다. 가입일은 이름이 아니라 member_id로 연결하게 했다."),
            "expect": [{"caption": "동호회별 기대 결과", "headers": ["동호회", "전액 불인정(사유)", "일부 인정", "인정 합계", "지급액"], "rows": [club_row(c) for c in b]}],
            "checks": ["가입일 경계: 사진 동호회에 정확히 30일(인정)과 29일(불인정)이 한 건씩 있다." if "사진" in b else "인정 합계와 지급액을 표에서 직접 더해 본다.",
                       "등산은 인정 합계가 30만 원을 넘어 지급액이 300,000원이어야 한다." if "등산" in b else "한도를 넘는 동호회가 없어야 한다. 넘는다면 건당 한도를 6만 원으로 썼는지 의심한다."],
        })
    all_bad = sorted(set(no for c in clubs for no in detail[c][0]))
    assert all_bad == disallowed
    paid_rows = [[c, f"{detail[c][2]:,}", f"{detail[c][3]:,}"] for c in clubs] + [["합계", "", f"{total_paid:,}"]]
    walk = {
        "goal": f"파일 29개 합계 약 {total_tokens:,}토큰이라 한 번에 붙일 수 없다. 기준 1회 → 영수증 전체 대조 1회 → 동호회 묶음 3회로 나누고, 마지막 취합은 손으로 한다. AI는 5회 쓴다.",
        "reading": [
            {"q": "1번", "need": "전액 불인정 영수증 번호 전체 (오름차순, 중복 번호는 한 번)", "src": "영수증·회원명단·가입일 + 규정 2~4·6조"},
            {"q": "2번", "need": "가입 30일 미만 청구 건수 (다른 사유와 겹쳐도 포함)", "src": "영수증 use_date, 가입일 + 규정 3조"},
            {"q": "3번", "need": "인정 합계가 30만 원을 넘는 동호회 (건당 5만 원 적용)", "src": "영수증 amount + 규정 5·7·8조"},
            {"q": "4번", "need": "동호회별 지급액(한도 적용) 합계", "src": "3번 계산 결과"},
        ],
        "plan": (f"1회차 규정+공고(614토큰) → 2회차 영수증.csv 9개({rec_tok:,}토큰) → 3~5회차 동호회 3곳씩 "
                 f"({', '.join(f'{t:,}' for t in batch_tok)}토큰) → 손으로 취합. 남는 5회는 어긋난 동호회만 좁혀서 다시 묻는 데 쓴다."),
        "batches": [{"label": f"묶음 {i + 1}", "clubs": b, "tokens": batch_tok[i]} for i, b in enumerate(batches)],
        "turns": turns3,
        "manual": {
            "title": "6단계: 결과 취합은 손으로",
            "text": "숫자 9개 더하기와 번호 정렬은 AI보다 손이 빠르고 정확하다. 남은 AI 횟수는 검증용으로 아낀다.",
            "tables": [
                {"caption": "가입 30일 미만 청구 (2번)", "headers": ["receipt_no", "동호회", "use_date", "가입일", "경과"], "rows": young_rows},
                {"caption": "동호회별 지급액 (3·4번)", "headers": ["동호회", "인정 합계", "지급액"], "rows": paid_rows},
            ],
        },
        "final": [
            {"q": "1번", "answer": ", ".join(disallowed), "how": f"묶음 1~3의 전액 불인정 번호를 합쳐 정렬, 중복 번호는 한 번만. 모두 {len(disallowed)}개"},
            {"q": "2번", "answer": f"{young}", "how": "위 표의 행 수. 볼링의 주류 영수증처럼 사유가 두 개인 건도 센다"},
            {"q": "3번", "answer": "① 등산", "how": f"건당 5만 원 기준 인정 합계: 등산 {final50['등산']:,}원만 30만 원 초과"},
            {"q": "4번", "answer": f"{total_paid}", "how": "동호회별 지급액 합 (등산은 300,000원으로 계산)"},
        ],
        "usage": "AI 5회 / 10회. 읽기 4분, 판정표 3분, 대조 4분, 묶음 3회 8분, 취합·입력 3분. 22분을 넘기기 쉬운 과제라 묶음 처리 중 대기 시간에 취합 표를 미리 그려 둔다.",
    }

    opts3 = ["등산", "등산, 풋살", "등산, 풋살, 밴드", "풋살", "한도를 넘는 동호회 없음"]
    reason_text = []
    for no in disallowed:
        reason_text.append(f"{no}({'/'.join(sorted(set(reasons[no])))})")
    paid_lines = ", ".join(f"{c} {paid[c]:,}" for c in clubs)

    task = {
        "id": "T3",
        "title": "동호회 활동비 정산 심사",
        "scenario": (
            "인사팀 복리후생 담당으로 9개 사내 동호회의 3분기 활동비 정산을 심사한다. 동호회마다 영수증·회원명단·가입일 파일이 있고, "
            "정산 규정과 공고문이 따로 있다. 파일 전체 토큰이 한 번에 첨부할 수 있는 양보다 많다."
        ),
        "cautions": [
            "공고문과 규정이 다르면 규정을 따른다.",
            "한 번 질문할 때 첨부할 수 있는 양이 정해져 있으니 묶어서 처리할 계획을 먼저 세운다.",
        ],
        "files": files,
        "questions": [
            {
                "id": "T3Q1", "type": "short", "unit": "",
                "prompt": "전액 인정되지 않는 영수증 번호를 오름차순으로 쉼표로 구분해 모두 쓰시오. (같은 번호는 한 번만)",
                "answer": ", ".join(disallowed), "list": True, "ordered": True,
                "why": f"전액 불인정 {len(disallowed)}건: " + ", ".join(reason_text) + ". 건당 5만 원 초과 영수증은 일부 인정이라 여기 들어가지 않는다.",
                "trap": "동호회를 따로 처리하면 등산·풋살 사이의 중복 청구를 놓친다. 마지막에 전체 번호를 한 번 더 대조해야 한다.",
            },
            {
                "id": "T3Q2", "type": "short", "unit": "건",
                "prompt": "'가입 후 30일 미만' 사유에 해당하는 청구는 몇 건인가? (다른 사유와 겹쳐도 포함, 숫자만)",
                "answer": str(young), "numeric": True,
                "why": "사용일 - 가입일 < 30인 청구를 센다. 사진 동호회의 7/31 사용 건은 정확히 30일이라 인정, 7/30 사용 건은 29일이라 위반이다. 볼링의 주류 영수증은 주류이면서 30일 미만이라 여기 포함된다.",
                "trap": "경계값 30일, 사유가 두 개인 영수증.",
            },
            {
                "id": "T3Q3", "type": "mc",
                "prompt": "동호회별 한도(30만 원) 때문에 지급액이 줄어드는 동호회를 빠짐없이 고른 것은?",
                "options": opts3, "answer": 0,
                "why": (
                    f"규정의 건당 5만 원 한도로 계산하면 인정 합계가 30만 원을 넘는 곳은 등산({final50['등산']:,}원)뿐이다. "
                    f"공고문의 6만 원을 쓰면 풋살이 {final60['풋살']:,}원이 되어 함께 걸리고, 건당 한도를 아예 빼면 밴드도 {nocap['밴드']:,}원으로 넘는다."
                ),
                "trap": "공고문(6만 원)과 규정(5만 원)이 충돌한다. 규정 제8조가 우선이다.",
            },
            {
                "id": "T3Q4", "type": "short", "unit": "원",
                "prompt": "9개 동호회 최종 지급액의 합계는 몇 원인가? (숫자만)",
                "answer": str(total_paid), "numeric": True,
                "why": f"동호회별 최종 지급액: {paid_lines}. 합계 {total_paid:,}원.",
                "trap": "등산은 인정액이 아니라 한도인 300,000원으로 더해야 한다.",
            },
        ],
        "promptExample": (
            "1차(규정+공고만 첨부): 두 문서로 동호회 영수증 판정표를 만들어줘. 조건별로 확인할 파일·열, 경계값(30일=인정, 퇴사일 당일=인정), "
            "공고와 규정이 다를 때 적용값(건당 5만 원)을 표로. 근거 조항 번호를 붙이고 문서에 없는 기준은 만들지 마.\n"
            "2차부터(동호회 3~4곳 파일 + 판정표 요약 직접 입력): 판정표 1~6을 적용해 영수증별로 '전액 불인정(사유)/일부 인정(인정액)/인정'을 표로. "
            "가입일은 member_id로 연결하고 이름으로 추정하지 마. 동호회별 인정액 합계와 한도 적용 후 지급액, 전액 불인정 번호 전체를 생략 없이 적어줘.\n"
            "마지막: 동호회별 결과만 모아서 중복 receipt_no를 다시 대조해."
        ),
        "lessons": [
            f"이 과제 파일 전체는 약 {total_tokens:,}토큰(추정)이라 한 번에 첨부할 수 없다. 규정 해석 1회 → 동호회 묶음 처리 → 결과 취합 순서로 계획한다.",
            "판정표를 먼저 만들고, 이후 질문에는 판정표 요약을 직접 입력한다. 이전 질문의 첨부 파일은 다음 질문에 따라오지 않는다고 가정하고 움직인다.",
            "동호회 간 중복처럼 묶음 사이에 걸친 조건은 마지막 취합 단계에서 따로 확인한다.",
        ],
        "walk": walk,
        "meta": {"final50": final50, "final60": final60, "nocap": nocap, "tokens": total_tokens,
                 "disallowed": {k: v for k, v in reasons.items()}},
    }
    return task


# ---------------------------------------------------------------------------
# 과제 4. SaaS 라이선스 비용 최적화
# ---------------------------------------------------------------------------

def task4():
    R = random.Random(4044)
    base = dt.date(2026, 9, 30)
    price = {"DocsAI": {"Business": 18000, "Pro": 9000},
             "DesignHub": {"Business": 32000, "Pro": 16000},
             "CodePilot": {"Business": 25000, "Pro": 12000}}
    depts = ["개발", "기획", "디자인", "영업", "재무", "인사", "품질"]
    rows = []
    n = [0]

    def add(tool, plan, dept, last, active):
        n[0] += 1
        rows.append({"uid": f"U{n[0]:03d}", "tool": tool, "plan": plan, "dept": dept,
                     "last": last, "active": active})

    def recent():
        return base - dt.timedelta(days=R.randint(0, 40))

    # DocsAI 32석: Business 14, Pro 18
    for i in range(14):
        add("DocsAI", "Business", R.choice(depts), recent(), R.randint(8, 22))
    for i in range(18):
        add("DocsAI", "Pro", R.choice(depts), recent(), R.randint(1, 20))
    # DesignHub 11석: Business 7, Pro 4
    for i in range(7):
        add("DesignHub", "Business", R.choice(["디자인", "기획", "영업"]), recent(), R.randint(7, 20))
    for i in range(4):
        add("DesignHub", "Pro", R.choice(["디자인", "기획"]), recent(), R.randint(2, 15))
    # CodePilot 20석: Business 12(개발 9, 기타 3), Pro 8
    for i in range(9):
        add("CodePilot", "Business", "개발", recent(), R.randint(9, 22))
    for i in range(3):
        add("CodePilot", "Business", R.choice(["기획", "품질"]), recent(), R.randint(9, 20))
    for i in range(8):
        add("CodePilot", "Pro", R.choice(["개발", "품질", "기획"]), recent(), R.randint(2, 18))

    by_tool = defaultdict(list)
    for r in rows:
        by_tool[r["tool"]].append(r)

    # 회수 대상 심기 (마지막 로그인 2026-07-31 이전 = 60일 초과)
    def set_last(r, d, active=0):
        r["last"] = d
        r["active"] = active

    d_pro = [r for r in by_tool["DocsAI"] if r["plan"] == "Pro"]
    d_bus = [r for r in by_tool["DocsAI"] if r["plan"] == "Business"]
    set_last(d_pro[0], dt.date(2026, 7, 31))     # 61일 -> 회수 (경계)
    set_last(d_pro[1], dt.date(2026, 6, 2))
    set_last(d_pro[2], dt.date(2026, 5, 17))
    set_last(d_bus[0], dt.date(2026, 7, 2))
    set_last(d_bus[1], dt.date(2026, 4, 9))
    set_last(d_pro[3], dt.date(2026, 8, 1), 0)   # 정확히 60일 -> 유지 (경계)
    g_bus = [r for r in by_tool["DesignHub"] if r["plan"] == "Business"]
    g_pro = [r for r in by_tool["DesignHub"] if r["plan"] == "Pro"]
    set_last(g_bus[0], dt.date(2026, 6, 20))
    set_last(g_pro[0], dt.date(2026, 7, 15))
    set_last(g_pro[1], dt.date(2026, 3, 30))
    c_bus_dev = [r for r in by_tool["CodePilot"] if r["plan"] == "Business" and r["dept"] == "개발"]
    c_bus_etc = [r for r in by_tool["CodePilot"] if r["plan"] == "Business" and r["dept"] != "개발"]
    c_pro = [r for r in by_tool["CodePilot"] if r["plan"] == "Pro"]
    set_last(c_bus_dev[0], dt.date(2026, 7, 20))
    set_last(c_pro[0], dt.date(2026, 6, 11))

    # 다운그레이드 대상 심기: Business, 회수 아님, 최근 30일 활성 5일 이하
    d_bus[2]["active"] = 5     # 경계: 5일 -> 다운그레이드
    d_bus[3]["active"] = 2
    d_bus[4]["active"] = 0
    d_bus[5]["active"] = 4
    d_bus[6]["active"] = 6     # 경계: 6일 -> 유지
    g_bus[1]["active"] = 3
    g_bus[2]["active"] = 1
    c_bus_dev[1]["active"] = 2   # 개발팀 CodePilot -> 예외로 유지
    c_bus_dev[2]["active"] = 4
    c_bus_dev[3]["active"] = 5
    c_bus_etc[0]["active"] = 3
    c_bus_etc[1]["active"] = 1

    R.shuffle(rows)

    # 정답 계산 ---------------------------------------------------------
    def reclaim(r):
        return (base - r["last"]).days > 60

    def downgrade(r):
        if reclaim(r) or r["plan"] != "Business" or r["active"] > 5:
            return False
        if r["tool"] == "CodePilot" and r["dept"] == "개발":
            return False
        return True

    q1 = sum(1 for r in rows if reclaim(r))
    after = []
    for r in rows:
        if reclaim(r):
            continue
        plan = "Pro" if downgrade(r) else r["plan"]
        after.append((r["tool"], plan))
    monthly = sum(price[t][p] for t, p in after)
    seats = defaultdict(int)
    for t, p in after:
        seats[t] += 1
    annual_tools = sorted([t for t in price if seats[t] >= 10])
    monthly_eq = 0
    for t, p in after:
        unit = price[t][p]
        if t in annual_tools:
            unit = int(round_half_up(unit * 0.8, 0))
        monthly_eq += unit
    before = sum(price[r["tool"]][r["plan"]] for r in rows)
    no_annual = sorted(t for t in price if t not in annual_tools)
    seats_before = defaultdict(int)
    for r in rows:
        seats_before[r["tool"]] += 1

    # 함정: 개발팀 예외를 빼먹은 경우의 월 비용
    trap_monthly = 0
    for r in rows:
        if reclaim(r):
            continue
        p = r["plan"]
        if (not reclaim(r)) and r["plan"] == "Business" and r["active"] <= 5:
            p = "Pro"
        trap_monthly += price[r["tool"]][p]

    assert no_annual == ["DesignHub"], (no_annual, seats)
    assert q1 == 10, q1

    # 풀이 가이드 데이터 ------------------------------------------------
    srt = sorted(rows, key=lambda x: x["uid"])
    rec_rows4 = [[r["uid"], r["tool"], r["plan"], r["last"].isoformat(), f"{(base - r['last']).days}일"] for r in srt if reclaim(r)]
    edge_rows4 = [[r["uid"], r["tool"], r["last"].isoformat(), f"{(base - r['last']).days}일", "유지 (정확히 60일)"] for r in srt if (base - r["last"]).days == 60]
    dg_rows4 = [[r["uid"], r["tool"], r["dept"], f"{r['active']}일"] for r in srt if downgrade(r)]
    ex_rows4 = [[r["uid"], r["tool"], r["dept"], f"{r['active']}일", "Business 유지 (개발 부서 예외)"] for r in srt
                if not reclaim(r) and r["plan"] == "Business" and r["active"] <= 5 and r["tool"] == "CodePilot" and r["dept"] == "개발"]
    six_rows4 = [[r["uid"], r["tool"], r["dept"], f"{r['active']}일", "유지 (6일)"] for r in srt if not reclaim(r) and r["plan"] == "Business" and r["active"] == 6]
    cnt_b = defaultdict(int)
    for r in rows:
        cnt_b[(r["tool"], r["plan"])] += 1
    cnt_a = defaultdict(int)
    for t, p in after:
        cnt_a[(t, p)] += 1
    seat_rows4 = []
    cost_rows4 = []
    eq_rows4 = []
    eq_sum_check = []
    for t in price:
        seat_rows4.append([t, f"{cnt_b[(t, 'Business')]} / {cnt_b[(t, 'Pro')]}", f"{cnt_a[(t, 'Business')]} / {cnt_a[(t, 'Pro')]}", f"{seats_before[t]} → {seats[t]}"])
        sub = cnt_a[(t, "Business")] * price[t]["Business"] + cnt_a[(t, "Pro")] * price[t]["Pro"]
        cost_rows4.append([t, f"{cnt_a[(t, 'Business')]}×{price[t]['Business']:,} + {cnt_a[(t, 'Pro')]}×{price[t]['Pro']:,}", f"{sub:,}"])
        if t in annual_tools:
            disc = {p: int(round_half_up(price[t][p] * 0.8, 0)) for p in ("Business", "Pro")}
            sub2 = cnt_a[(t, "Business")] * disc["Business"] + cnt_a[(t, "Pro")] * disc["Pro"]
            eq_sum_check.append(sub2)
            eq_rows4.append([t, f"{seats[t]}석 → 가능", f"{cnt_a[(t, 'Business')]}×{disc['Business']:,} + {cnt_a[(t, 'Pro')]}×{disc['Pro']:,}", f"{sub2:,}"])
        else:
            eq_sum_check.append(sub)
            eq_rows4.append([t, f"{seats[t]}석 → 불가", "할인 없음", f"{sub:,}"])
    assert sum(eq_sum_check) == monthly_eq, (eq_sum_check, monthly_eq)
    cost_rows4.append(["합계", "", f"{monthly:,}"])
    eq_rows4.append(["합계", "", "", f"{monthly_eq:,}"])
    t4_turn1 = (
        "[라이선스_정리_기준.md]를 2→3→4 순서로 적용해 1~4번에 필요한 값을 한 번에 계산해줘.\n"
        "①기준일 2026-09-30 − last_login이 60일을 넘는 좌석: user_id·last_login·경과일 목록과 수 (정확히 60일은 유지)\n"
        "②회수 제외 후 Business이면서 active_days_30d ≤ 5인 좌석 목록 (개발 부서 CodePilot은 예외로 따로 표시)\n"
        "③도구별·플랜별 좌석 수 표 (정리 전/후)\n④월 비용 = 좌석 수×단가로 도구별 소계와 합계\n"
        "⑤정리 후 10석 이상인 도구만 단가×0.8을 적용한 월 환산 합계, 연간 결제 불가 도구\n"
        "모든 계산은 식과 중간값을 보여주고, 목록은 user_id로 생략 없이 적어줘."
    )
    t4_turn2 = (
        "경계값만 다시 확인해줘: last_login이 2026-07-31, 2026-08-01인 좌석, active_days_30d가 5·6인 Business 좌석, "
        "개발 부서 CodePilot 중 active_days_30d ≤ 5인 좌석. 각각 기준 몇 번에 따라 어떻게 판정되는지 한 줄씩."
    )
    walk = {
        "goal": "파일 2개 1,368토큰. 1회차에 회수·다운그레이드·좌석·비용을 표로 받고, 금액은 좌석 수 표만 믿고 내가 곱한다.",
        "reading": [
            {"q": "1번", "need": "기준일 − last_login > 60일 좌석 수 (60일 정각은 유지)", "src": "licenses, 기준 2"},
            {"q": "2번", "need": "회수 제외 → Business·활성 5일 이하 → Pro (개발 CodePilot 예외) → 월 비용", "src": "licenses, 기준 1·3"},
            {"q": "3번", "need": "정리 후 10석 이상 도구만 20% 할인한 월 환산 합계", "src": "2번 결과 + 기준 4"},
            {"q": "4번", "need": "정리 후 10석 미만 도구", "src": "2번 좌석 수"},
        ],
        "plan": "첨부 2개 전부 → 1회차 일괄. 경계값이 의심되면 2회차로 경계 행만 확인.",
        "turns": [
            {
                "n": 1, "title": "회수 → 다운그레이드 → 비용 → 연간 결제 일괄",
                "select": [1, 2, 3, 4], "attach": ["licenses.csv", "라이선스_정리_기준.md"],
                "prompt": t4_turn1,
                "why": "기준 문서의 적용 순서(회수 → 다운그레이드 → 연간 결제)를 그대로 번호로 박았다. 좌석 수 표만 정확하면 금액은 손으로 바로 검산된다.",
                "expect": [
                    {"caption": "① 회수 대상 (1번)", "headers": ["user_id", "도구", "플랜", "last_login", "경과"], "rows": rec_rows4},
                    {"caption": "경계: 정확히 60일", "headers": ["user_id", "도구", "last_login", "경과", "판정"], "rows": edge_rows4},
                    {"caption": "② 다운그레이드 대상", "headers": ["user_id", "도구", "부서", "활성일"], "rows": dg_rows4},
                    {"caption": "② 예외·경계로 유지", "headers": ["user_id", "도구", "부서", "활성일", "판정"], "rows": ex_rows4 + six_rows4},
                    {"caption": "③ 좌석 수 (Business / Pro)", "headers": ["도구", "정리 전", "정리 후", "합계 변화"], "rows": seat_rows4},
                    {"caption": "④ 월 비용 (2번)", "headers": ["도구", "식", "월 비용"], "rows": cost_rows4},
                    {"caption": "⑤ 연간 결제 월 환산 (3·4번)", "headers": ["도구", "연간 결제", "식", "월 환산"], "rows": eq_rows4},
                ],
                "checks": [
                    "회수 목록에 last_login 2026-08-01(정확히 60일)이 들어 있으면 틀린 것이다.",
                    "개발 부서 CodePilot의 저활성 좌석이 다운그레이드 목록에 있으면 예외를 놓친 것이다. 이 경우 월 비용이 더 낮게 나온다.",
                    "활성일 5일은 다운그레이드, 6일은 유지다.",
                    "DesignHub는 정리 전 11석이지만 정리 후 8석이라 연간 결제가 안 된다. 정리 전 좌석으로 판단했는지 본다.",
                    "금액은 표 ③의 좌석 수에 단가를 곱해 직접 더한다. AI가 쓴 합계를 그대로 옮기지 않는다.",
                ],
            },
            {
                "n": 2, "title": "(선택) 경계값만 확인",
                "select": [1, 2], "attach": ["licenses.csv", "라이선스_정리_기준.md"],
                "prompt": t4_turn2,
                "why": "이 과제의 함정은 전부 경계값과 예외다. 1회차 목록이 맞는지 의심되면 경계 행만 좁혀 묻는다.",
                "expect": [{"caption": "기대 판정", "headers": ["user_id", "도구", "값", "경과/활성", "판정"],
                            "rows": [[r[0], r[1], r[3], r[4], "회수 (61일)"] for r in rec_rows4 if r[4] == "61일"] + [[r[0], r[1], r[2], r[3], r[4]] for r in edge_rows4]
                            + [[r[0], r[1], r[2], r[3], "Pro로 변경"] for r in dg_rows4 if r[3] == "5일"] + [[r[0], r[1], r[2], r[3], r[4]] for r in six_rows4] + [[r[0], r[1], r[2], r[3], r[4]] for r in ex_rows4]}],
                "checks": ["판정이 1회차와 같으면 1회차 목록을 믿고 진행한다."],
            },
        ],
        "final": [
            {"q": "1번", "answer": f"{q1}", "how": "① 표의 행 수"},
            {"q": "2번", "answer": f"{monthly}", "how": " + ".join(f"{t} {r[2]}" for t, r in zip(price, cost_rows4))},
            {"q": "3번", "answer": f"{monthly_eq}", "how": f"{', '.join(annual_tools)}만 20% 할인, DesignHub는 정가"},
            {"q": "4번", "answer": "② DesignHub", "how": f"정리 후 {seats['DesignHub']}석 < 10석"},
        ],
        "usage": "AI 1회(경계 확인까지 2회) / 10회. 읽기 3분, 프롬프트 3분, 검증·곱셈 8분, 입력 2분.",
    }

    f_lic = csv_text(["user_id", "tool", "plan", "dept", "last_login", "active_days_30d"],
                     [(r["uid"], r["tool"], r["plan"], r["dept"], r["last"].isoformat(), r["active"]) for r in sorted(rows, key=lambda x: x["uid"])])
    f_policy = """# 협업 SaaS 라이선스 정리 기준 (구매팀)

기준일: 2026-09-30

## 1. 요금 (1좌석 월 단가, 원)
| 도구 | Business | Pro |
|---|---|---|
| DocsAI | 18,000 | 9,000 |
| DesignHub | 32,000 | 16,000 |
| CodePilot | 25,000 | 12,000 |

## 2. 회수
- 기준일에서 마지막 로그인일(last_login)을 뺀 날수가 60일을 넘으면 좌석을 회수한다. 정확히 60일이면 회수하지 않는다.

## 3. 다운그레이드
- 회수 대상이 아니고, Business 플랜이며, 최근 30일 활성일(active_days_30d)이 5일 이하인 좌석은 Pro로 바꾼다.
- 예외: 개발 부서(dept=개발)의 CodePilot은 보안 정책상 Business를 유지한다.

## 4. 연간 결제
- 연간 결제 시 월 단가를 20% 할인한다.
- 연간 결제는 회수·다운그레이드를 반영한 뒤 그 도구의 좌석이 10석 이상일 때만 가능하다.
- 할인 단가에 원 미만이 생기면 원 단위로 반올림한다.
"""
    files = [
        {"name": "licenses.csv", "kind": "csv", "text": f_lic},
        {"name": "라이선스_정리_기준.md", "kind": "doc", "text": f_policy},
    ]
    opts4 = ["DocsAI", "DesignHub", "CodePilot", "DesignHub, CodePilot", "없음 (세 도구 모두 가능)"]
    seat_line = ", ".join(f"{t} {seats_before[t]}석→{seats[t]}석" for t in price)
    task = {
        "id": "T4",
        "title": "협업 SaaS 라이선스 비용 정리",
        "scenario": (
            "구매팀에서 사내 협업 SaaS 3종(DocsAI, DesignHub, CodePilot)의 라이선스를 정리한다. "
            "안 쓰는 좌석은 회수하고, 적게 쓰는 좌석은 낮은 플랜으로 바꾸고, 가능한 도구는 연간 결제로 전환하려 한다."
        ),
        "cautions": ["정리 기준의 순서(회수 → 다운그레이드 → 연간 결제)대로 적용한다.", "금액은 원 단위로 답한다."],
        "files": files,
        "questions": [
            {
                "id": "T4Q1", "type": "short", "unit": "석",
                "prompt": "회수 대상 좌석은 모두 몇 석인가? (숫자만)",
                "answer": str(q1), "numeric": True,
                "why": f"last_login이 2026-07-31 이전(60일 초과)인 좌석이 {q1}석이다. 2026-08-01 로그인은 정확히 60일이라 유지, 2026-07-31은 61일이라 회수.",
                "trap": "'60일 초과'와 '60일 이상'의 차이.",
            },
            {
                "id": "T4Q2", "type": "short", "unit": "원",
                "prompt": "회수와 다운그레이드를 반영한 뒤, 월 결제 기준 월 비용 합계는 몇 원인가? (숫자만)",
                "answer": str(monthly), "numeric": True,
                "why": f"정리 전 월 {before:,}원 → 회수·다운그레이드 반영 후 월 {monthly:,}원. 개발팀 CodePilot 예외를 빼먹으면 {trap_monthly:,}원이 나온다.",
                "trap": "개발팀 CodePilot 예외, 활성일 5일 경계(5일은 다운그레이드, 6일은 유지).",
            },
            {
                "id": "T4Q3", "type": "short", "unit": "원",
                "prompt": "2번 상태에서 연간 결제가 가능한 도구를 모두 연간 결제로 바꾸면, 월 환산 비용 합계는 몇 원인가? (숫자만)",
                "answer": str(monthly_eq), "numeric": True,
                "why": f"좌석 수 {seat_line}. 10석 이상인 {', '.join(annual_tools)}만 20% 할인. 월 환산 합계 {monthly_eq:,}원.",
                "trap": "정리 전 좌석 수로 10석을 판단하면 DesignHub도 할인한다고 착각한다.",
            },
            {
                "id": "T4Q4", "type": "mc",
                "prompt": "연간 결제를 적용할 수 없는 도구는?",
                "options": opts4, "answer": opts4.index("DesignHub"),
                "why": f"정리 후 DesignHub가 {seats['DesignHub']}석이라 10석 미만이다. 정리 전에는 {seats_before['DesignHub']}석이었다.",
                "trap": "판단 시점(정리 전/후).",
            },
        ],
        "promptExample": (
            "[라이선스_정리_기준.md]를 2→3→4 순서로 적용해 1~4번에 필요한 값을 한 번에 계산해줘.\n"
            "①기준일 2026-09-30 - last_login > 60일인 좌석 목록과 수(정확히 60일은 유지) "
            "②회수 제외 후 Business이면서 active_days_30d ≤ 5인 좌석(개발 부서 CodePilot 제외) 목록 "
            "③도구별·플랜별 좌석 수 표(정리 전/후) ④월 비용 = 좌석 수×단가 식으로 도구별 소계와 합계 "
            "⑤정리 후 10석 이상 도구만 단가×0.8 적용한 월 환산 합계.\n"
            "모든 계산은 식과 중간값을 보여주고, 목록은 user_id로 생략 없이 적어줘."
        ),
        "lessons": [
            "단계가 정해진 계산은 '순서'를 프롬프트에 박아 두면 AI가 단계를 건너뛰지 않는다.",
            "도구별·플랜별 좌석 수 표만 받으면 금액은 내가 직접 곱해서 검산할 수 있다.",
            "예외 조항(개발팀 CodePilot)은 별도 줄로 다시 확인한다.",
        ],
        "walk": walk,
        "meta": {"monthly": monthly, "monthly_eq": monthly_eq, "seats": dict(seats), "before": before, "trap_monthly": trap_monthly},
    }
    return task


def main():
    tasks = [task1(), task2(), task3(), task4()]
    for t in tasks:
        for f in t["files"]:
            f["tokens"] = est_tokens(f["text"])
        t["totalTokens"] = sum(f["tokens"] for f in t["files"])
        names = {f["name"]: f["tokens"] for f in t["files"]}
        for turn in t["walk"]["turns"]:
            assert len(turn["prompt"]) <= 1000, (t["id"], turn["n"], len(turn["prompt"]))
            assert all(n in names for n in turn["attach"]), (t["id"], turn["n"])
            turn["attachTokens"] = sum(names[n] for n in turn["attach"])
            turn["promptChars"] = len(turn["prompt"])
            assert turn["attachTokens"] <= 20000, (t["id"], turn["n"], turn["attachTokens"])
            print(f"   walk {t['id']} turn {turn['n']}: prompt {turn['promptChars']}자, attach {turn['attachTokens']:,}토큰")
    payload = json.dumps(tasks, ensure_ascii=False, indent=1, default=str)
    OUT.write_text(
        "/* 자동 생성 파일: tools/gen_tasks.py 를 실행해서 만든다. 직접 고치지 말 것. */\n"
        f"window.TASKS = {payload};\n",
        encoding="utf-8",
    )
    for t in tasks:
        print(t["id"], t["title"], "files", len(t["files"]), "tokens~", t["totalTokens"])
        for q in t["questions"]:
            ans = q["answer"] if q["type"] != "mc" else f"{q['answer']}:{q['options'][q['answer']]}"
            print("   ", q["id"], q["type"], "=>", ans)


if __name__ == "__main__":
    main()
