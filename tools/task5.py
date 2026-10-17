"""과제 5. 웨이퍼 출하 전 최종 검사 불량 판정 (10/17 후기의 '불량 판별' 과제를 본떠 만든 연습 과제)

첨부가 많고(12개), 전부 넣으면 한도를 넘고, 넣을 수 있는 만큼 넣어도 내장 AI가 헷갈린다.
→ 기준 정리 1회(메타프롬프트) → 일자 파일 2개씩 3회 → 손으로 취합.

정답은 이 스크립트가 규칙대로 계산한다. 값은 0.01nm 단위 정수로 다뤄 부동소수 오차를 없앴다.
"""
import random
import datetime as dt
from collections import defaultdict

WIN_S = dt.datetime(2026, 10, 13, 6, 0)
WIN_E = dt.datetime(2026, 10, 14, 18, 0)
THK_LO, THK_HI = 4800, 5200      # 48.00 ~ 52.00 nm (경계 포함 합격)
PC_MAX = 20                      # 20개 이하 합격
CD_LO, CD_HI = 2820, 2980        # 28.20 ~ 29.80 nm (경계 포함 합격)
CORR = 60                        # MT-03 THK 0.60nm 높게 측정됨 → 60 빼기


def f2(v):
    return f"{v // 100}.{v % 100:02d}"


def build(csv_text):
    R = random.Random(5055)
    names = ["김도윤", "이서준", "박지호", "최하린", "정민서", "강예준", "윤서아", "한지민"]
    tools = ["MT-01", "MT-02", "MT-03", "MT-04"]

    def base_vals():
        return {"thk": R.randint(4870, 5140), "pc": R.randint(0, 14), "cd": R.randint(2852, 2948), "note": ""}

    # ------------------------------------------------------------ 심어 둔 로트
    # key: (day, "HH:MM" 또는 None, tool 또는 None, {wafer index: {필드: 값}})
    P = {
        # 보정 때문에 판정이 바뀌는 로트
        "A":  (13, "10:20", "MT-03", {0: {"thk": 5240}, 2: {"pc": 22}}),            # 52.40→51.80 합격, 불량 1장 → 합격 (보정 안 하면 불량)
        "A2": (14, "09:10", "MT-03", {1: {"thk": 5225}, 3: {"cd": 2818}}),          # 52.25→51.65 합격 → 합격 (보정 안 하면 불량)
        "B":  (14, "15:05", "MT-03", {2: {"thk": 4850}, 4: {"cd": 2995}}),          # 48.50→47.90 불량 → 불량 (보정 안 하면 합격)
        # 보정 대상이 아닌데 보정하면 바뀌는 로트 (함정)
        "C":  (14, "18:30", "MT-03", {0: {"thk": 5230}, 3: {"pc": 24}}),            # 기간 끝(18:00) 뒤 → 보정 없음 → 불량
        "D":  (13, "13:40", "MT-02", {1: {"thk": 5220}, 4: {"cd": 2810}}),          # MT-02 → 보정 없음 → 불량
        "M":  (15, "08:15", "MT-03", {1: {"thk": 4780}, 4: {"thk": 5245}}),         # 10/15 → 보정 없음 → 불량
        # 기간 시작 정각(06:00, 양 끝 포함) → 보정 대상. 로트는 어차피 불량, 불량 웨이퍼 수만 달라짐
        "E":  (13, "06:00", "MT-03", {0: {"thk": 5255}, 2: {"pc": 28}, 3: {"cd": 2986}}),
        # 재측정
        "F":  (12, "11:15", "MT-01", {1: {"pc": 23}, 3: {"thk": 4760}}),            # PC 23→17 → 불량 1장 → 합격
        "G":  (15, "10:50", "MT-04", {0: {"thk": 5190}, 2: {"cd": 2985}}),          # THK 51.90→52.10 → 불량 2장 → 불량 (특채 승인)
        "H":  (15, "14:30", "MT-02", {1: {"pc": 26}, 4: {"cd": 2990}}),             # CD 29.90→29.85 여전히 불량 → 불량 (특채 반려)
        "I":  (16, "09:35", "MT-01", {0: {"pc": 21}, 2: {"thk": 5260, "cd": 2805}}),  # THK만 재측정 50.20, CD 28.05는 그대로 불량
        "K":  (13, "14:20", "MT-04", {1: {"pc": 22}, 3: {"thk": 4750}}),            # PC 22→21→19(마지막) → 합격
        # 일반 불량 로트
        "J":  (12, "15:45", "MT-02", {0: {"thk": 5235}, 2: {"pc": 25}}),
        "L":  (14, "11:25", "MT-01", {0: {"cd": 2992}, 1: {"cd": 2811}, 3: {"pc": 30}}),
        "N":  (16, "13:05", "MT-04", {2: {"pc": 21}, 4: {"cd": 2981}}),
        # 불량 웨이퍼 1장뿐인 로트 (합격). 경계값 합격 웨이퍼를 같이 넣었다
        "S1":  (12, None, "MT-01", {0: {"thk": 5201}, 2: {"thk": 5200}}),
        "S2":  (12, None, "MT-04", {1: {"cd": 2819}, 3: {"cd": 2820}}),
        "S3":  (13, None, "MT-02", {0: {"pc": 21}, 4: {"pc": 20}}),
        "S4":  (13, None, "MT-04", {2: {"cd": 2981}, 0: {"cd": 2980}}),
        "S5":  (14, "19:20", "MT-02", {3: {"thk": 4799}, 1: {"thk": 4800}}),
        "S6":  (14, None, "MT-04", {0: {"pc": 27}}),
        "S7":  (15, None, "MT-01", {2: {"thk": 5280}}),
        "S8":  (15, None, "MT-04", {1: {"cd": 3010}}),
        "S9":  (16, None, "MT-02", {3: {"pc": 35}, 1: {"note": "스크래치 의심(육안)"}}),
        "S10": (16, None, "MT-04", {4: {"thk": 4720}}),
        "S11": (12, None, "MT-04", {2: {"pc": 22, "note": "재측정 요청"}}),
        # 깨끗한 로트인데 특채 승인 메모에 이름이 있는 로트
        "X":  (16, None, "MT-01", {}),
    }
    counts = {12: 22, 13: 24, 14: 24, 15: 22, 16: 20}

    def rand_time(day, used):
        while True:
            t = dt.datetime(2026, 10, day, 7, 0) + dt.timedelta(minutes=5 * R.randint(0, 175))
            if t not in used and not (day == 14 and dt.time(17, 40) <= t.time() <= dt.time(18, 50)):
                used.add(t)
                return t

    lots = []  # dict(key, day, start, tool, product, wafers[list of dict(w, thk, pc, cd, note, t)])
    for day, n in counts.items():
        used = set()
        planted = [(k, v) for k, v in P.items() if v[0] == day]
        for k, (d, hm, tool, ov) in planted:
            if hm:
                h, m = map(int, hm.split(":"))
                start = dt.datetime(2026, 10, d, h, m)
                used.add(start)
            else:
                start = rand_time(day, used)
            lots.append({"key": k, "day": day, "start": start, "tool": tool or R.choice(tools), "product": "HBM-D7", "ov": ov})
        for _ in range(n - len(planted)):
            lots.append({"key": None, "day": day, "start": rand_time(day, used), "tool": R.choice(tools), "product": "HBM-D7", "ov": {}})
        for _ in range(2):  # DDR5-X2 개발 로트 (판정 대상 아님, HBM 규격으로 재면 전부 불량)
            lots.append({"key": "DDR5", "day": day, "start": rand_time(day, used), "tool": R.choice(tools), "product": "DDR5-X2", "ov": {}})
    # 지난주 금요일 파일 (기간 밖)
    prev = []
    used = set()
    prev_bad = {0: {0: {"thk": 5250}, 3: {"pc": 26}}, 1: {1: {"cd": 2800}, 2: {"thk": 4770}}, 2: {0: {"pc": 31}, 4: {"cd": 3002}}, 3: {2: {"pc": 23}}, 4: {1: {"thk": 5212}}}
    for i in range(20):
        t = dt.datetime(2026, 10, 9, 7, 0) + dt.timedelta(minutes=5 * R.randint(0, 175))
        while t in used:
            t += dt.timedelta(minutes=5)
        used.add(t)
        prev.append({"key": "PREV", "day": 9, "start": t, "tool": R.choice(tools), "product": "HBM-D7", "ov": prev_bad.get(i, {})})

    # 웨이퍼 값 채우기
    for L in lots + prev:
        ws = sorted(R.sample(range(1, 26), 5))
        wafers = []
        for i, w in enumerate(ws):
            v = base_vals()
            if L["product"] == "DDR5-X2":
                v["thk"] = R.randint(5310, 5480)      # DDR5 규격은 다르다. HBM 규격으로 보면 불량
                v["pc"] = R.randint(5, 30)
            v.update(L["ov"].get(i, {}))
            v["w"] = f"W{w:02d}"
            v["t"] = L["start"] + dt.timedelta(minutes=3 * i)
            v["who"] = names[R.randrange(len(names))]
            if not v["note"] and R.random() < 0.04:
                v["note"] = "육안 이상 없음"
            wafers.append(v)
        L["wafers"] = wafers

    # 로트 ID: 시간순으로 번호를 매긴다
    allw = sorted(lots, key=lambda x: x["start"])
    for i, L in enumerate(allw):
        L["id"] = f"L2610-{201 + i:04d}"
    for i, L in enumerate(sorted(prev, key=lambda x: x["start"])):
        L["id"] = f"L2610-{101 + i:04d}"
    KEY = {L["key"]: L for L in lots if L["key"] not in (None, "DDR5")}
    prev_sorted = sorted(prev, key=lambda x: x["start"])
    ddr = [L for L in lots if L["product"] == "DDR5-X2"]

    def wid(k, i):
        return KEY[k]["id"], KEY[k]["wafers"][i]["w"]

    # 재측정 기록 ---------------------------------------------------------
    remeasure = [
        # (lot_id, wafer, product, item, before, after, time, reason)
        (*wid("F", 1), "HBM-D7", "PC", 23, 17, dt.datetime(2026, 10, 12, 16, 40), "파티클 카운터 오염 의심"),
        (*wid("K", 1), "HBM-D7", "PC", 22, 21, dt.datetime(2026, 10, 13, 15, 10), "재측정 요청"),
        (*wid("K", 1), "HBM-D7", "PC", 21, 19, dt.datetime(2026, 10, 13, 18, 40), "세정 후 2차 재측정"),
        (*wid("G", 0), "HBM-D7", "THK_nm", 5190, 5210, dt.datetime(2026, 10, 15, 13, 20), "측정 위치 오류 의심"),
        (*wid("H", 4), "HBM-D7", "CD_nm", 2990, 2985, dt.datetime(2026, 10, 15, 17, 5), "고객 요청 재확인"),
        (*wid("I", 2), "HBM-D7", "THK_nm", 5260, 5020, dt.datetime(2026, 10, 16, 11, 30), "센서 노이즈"),
        (ddr[3]["id"], ddr[3]["wafers"][1]["w"], "DDR5-X2", "CD_nm", ddr[3]["wafers"][1]["cd"], ddr[3]["wafers"][1]["cd"] - 12, ddr[3]["start"] + dt.timedelta(hours=2), "개발 평가용"),
        (prev_sorted[0]["id"], prev_sorted[0]["wafers"][0]["w"], "HBM-D7", "THK_nm",
         prev_sorted[0]["wafers"][0]["thk"], 5080, prev_sorted[0]["start"] + dt.timedelta(hours=3), "지난주 재측정"),
    ]
    # 재측정 원측정값이 검사결과와 맞는지 확인 (첫 기록만 원래 값)
    first = {}
    for lot_id, w, prod, item, before, after, t, why in remeasure:
        first.setdefault((lot_id, w, item), before)
    allmap = {(L["id"], x["w"]): x for L in lots + prev for x in L["wafers"]}
    fld = {"PC": "pc", "THK_nm": "thk", "CD_nm": "cd"}
    for (lot_id, w, item), before in first.items():
        assert allmap[(lot_id, w)][fld[item]] == before, (lot_id, w, item)

    # 판정 ---------------------------------------------------------------
    def evaluate(corr="window", remeas="last", whole=False, spec="v3", boundary_ok=True, products=("HBM-D7",), with_prev=False, corr_tools=("MT-03",)):
        rm = defaultdict(list)
        for lot_id, w, prod, item, before, after, t, why in remeasure:
            rm[(lot_id, w, fld[item])].append((t, after))
        pc_max = 20 if spec == "v3" else 25
        lot_bad_min = 2 if spec == "v3" else 3
        out = {}
        pool = lots + (prev if with_prev else [])
        for L in pool:
            if L["product"] not in products:
                continue
            if not with_prev and L["day"] == 9:
                continue
            bad_w = []
            for x in L["wafers"]:
                v = {"thk": x["thk"], "pc": x["pc"], "cd": x["cd"]}
                if corr == "window" and L["tool"] in corr_tools and WIN_S <= x["t"] <= WIN_E:
                    v["thk"] -= CORR
                elif corr == "all_mt03" and L["tool"] == "MT-03":
                    v["thk"] -= CORR
                elif corr == "window_excl" and L["tool"] in corr_tools and WIN_S < x["t"] < WIN_E:
                    v["thk"] -= CORR
                replaced = set()
                if remeas != "none":
                    for k in ("thk", "pc", "cd"):
                        hist = sorted(rm.get((L["id"], x["w"], k), []))
                        if hist:
                            v[k] = hist[-1][1] if remeas == "last" else hist[0][1]
                            replaced.add(k)
                reasons = []
                if boundary_ok:
                    if not (THK_LO <= v["thk"] <= THK_HI): reasons.append("THK")
                    if v["pc"] > pc_max: reasons.append("PC")
                    if not (CD_LO <= v["cd"] <= CD_HI): reasons.append("CD")
                else:
                    if not (THK_LO < v["thk"] < THK_HI): reasons.append("THK")
                    if v["pc"] >= pc_max: reasons.append("PC")
                    if not (CD_LO < v["cd"] < CD_HI): reasons.append("CD")
                if whole and replaced:
                    # 함정 풀이: 재측정한 항목이 합격이면 웨이퍼 전체를 합격으로 보는 잘못된 처리
                    okk = {"thk": THK_LO <= v["thk"] <= THK_HI, "pc": v["pc"] <= pc_max, "cd": CD_LO <= v["cd"] <= CD_HI}
                    if all(okk[k] for k in replaced):
                        reasons = []
                if reasons:
                    bad_w.append((x, reasons, v))
            out[L["id"]] = {"lot": L, "bad": bad_w, "hold": len(bad_w) >= lot_bad_min}
        return out

    res = evaluate()
    hold = sorted(k for k, r in res.items() if r["hold"])
    n_lots = len(res)
    n_badw = sum(len(r["bad"]) for r in res.values())
    approved = [KEY["G"]["id"], KEY["X"]["id"]]
    rejected = [KEY["H"]["id"]]
    no_ship = [k for k in hold if k not in approved]
    ship_ratio = (n_lots - len(no_ship)) / n_lots * 100

    # 보정 적용 여부로 바뀌는 로트
    res_nc = evaluate(corr="none")
    changed = sorted(k for k in res if res[k]["hold"] != res_nc[k]["hold"])
    assert changed == sorted([KEY["A"]["id"], KEY["A2"]["id"], KEY["B"]["id"]]), changed
    # 설계 확인: 심은 로트의 판정
    expect_hold = {"A": False, "A2": False, "B": True, "C": True, "D": True, "E": True, "F": False, "G": True, "H": True, "I": True,
                   "K": False, "J": True, "L": True, "M": True, "N": True, "X": False}
    for k, h in expect_hold.items():
        assert res[KEY[k]["id"]]["hold"] == h, (k, res[KEY[k]["id"]]["hold"])
    for k in [k for k in P if k.startswith("S")]:
        assert not res[KEY[k]["id"]]["hold"] and len(res[KEY[k]["id"]]["bad"]) == 1, k
    base_bad = [k for k, r in res.items() if r["lot"]["key"] is None and r["bad"]]
    assert not base_bad, base_bad
    assert len(hold) == 11, hold

    # 함정 풀이가 다른 답을 내는지
    traps = {
        "보정 안 함": evaluate(corr="none"),
        "MT-03 전 기간 보정": evaluate(corr="all_mt03"),
        "모든 장비 보정": evaluate(corr_tools=("MT-01", "MT-02", "MT-03", "MT-04")),
        "기간 양 끝 제외": evaluate(corr="window_excl"),
        "재측정 무시": evaluate(remeas="none"),
        "첫 재측정값": evaluate(remeas="first"),
        "웨이퍼 통째 교체": evaluate(whole=True),
        "v2 기준": evaluate(spec="v2"),
        "경계값 불량": evaluate(boundary_ok=False),
        "DDR5 포함": evaluate(products=("HBM-D7", "DDR5-X2")),
        "지난주 포함": evaluate(with_prev=True),
    }
    trap_q1 = {k: sum(r["hold"] for r in v.values()) for k, v in traps.items()}
    trap_q4 = {k: sum(len(r["bad"]) for r in v.values()) for k, v in traps.items()}

    # 파일 ---------------------------------------------------------------
    def day_file(day_lots):
        rows = []
        for L in day_lots:
            for x in L["wafers"]:
                rows.append((x["t"], L["id"], x["w"], L["product"], x["t"].strftime("%Y-%m-%d %H:%M"), L["tool"], f2(x["thk"]), x["pc"], f2(x["cd"]), x["who"], x["note"]))
        rows.sort(key=lambda r: (r[0], r[1], r[2]))
        return csv_text(["lot_id", "wafer", "product", "measured_at", "tool", "THK_nm", "PC", "CD_nm", "측정자", "비고"], [r[1:] for r in rows])

    files = []
    std_v3 = """# 웨이퍼 출하 전 최종 검사 판정 기준 v3 (HBM-D7)
문서번호 QA-STD-117 / 시행 2026-10-01 / v2 대비 변경: 파티클 기준, 로트 판정 기준

제1조(대상) 제품 HBM-D7의 측정일 2026-10-12 ~ 2026-10-16 최종 검사 결과를 판정한다. 다른 제품(DDR5-X2 등 개발 로트)은 이 기준으로 판정하지 않는다.

제2조(웨이퍼 판정) 아래 세 항목이 모두 규격 안이면 합격, 하나라도 벗어나면 불량 웨이퍼다. 경계값은 합격이다.
1. 막두께 THK_nm: 48.00 이상 52.00 이하
2. 파티클 PC: 20개 이하
3. 임계치수 CD_nm: 28.20 이상 29.80 이하

제3조(로트 판정) 로트당 측정 웨이퍼 5장 중 불량 웨이퍼가 2장 이상이면 로트 불량(HOLD), 1장 이하이면 로트 합격이다.

제4조(재측정) 재측정 기록이 있는 웨이퍼는 재측정한 항목만 재측정값으로 바꿔 판정한다. 다른 항목은 원래 측정값을 쓴다. 같은 항목을 여러 번 재측정했으면 마지막 값을 쓴다.

제5조(장비 보정) 측정 장비 보정 공지가 있으면 공지에 적힌 장비·기간·항목의 측정값을 보정한 뒤 판정한다.

제6조(특채) 품질팀장이 특채를 승인한 로트는 판정 결과를 바꾸지 않고(불량은 불량으로 집계) 출하 가능으로 분류한다. 승인되지 않은 불량 로트는 출하할 수 없다.

제7조(비고란) 비고란의 육안 소견과 요청 사항은 판정에 쓰지 않는다. 판정은 측정값과 재측정 기록으로만 한다.
"""
    std_v2 = """# 웨이퍼 출하 전 최종 검사 판정 기준 v2 (HBM-D7)
문서번호 QA-STD-117 / 시행 2026-04-01 / ※ 2026-09-30 폐기, v3로 대체

제1조(대상) 제품 HBM-D7의 출하 전 최종 검사 결과를 판정한다.

제2조(웨이퍼 판정) 아래 세 항목이 모두 규격 안이면 합격이다.
1. 막두께 THK_nm: 48.00 이상 52.00 이하
2. 파티클 PC: 25개 이하
3. 임계치수 CD_nm: 28.20 이상 29.80 이하

제3조(로트 판정) 로트당 측정 웨이퍼 5장 중 불량 웨이퍼가 3장 이상이면 로트 불량이다.

제4조(재측정) 재측정 값이 있으면 재측정 값으로 판정한다.
"""
    notice = """# [공지] MT-03 막두께(THK) 측정값 보정 안내
작성: 계측기술팀 / 2026-10-14 19:20

- 대상 장비: MT-03 (다른 계측 장비는 해당 없음)
- 대상 기간: 2026-10-13 06:00 ~ 2026-10-14 18:00 (measured_at 기준, 시작과 끝 시각 포함)
- 내용: 위 기간에 MT-03으로 잰 THK_nm 값이 실제보다 0.60nm 높게 측정되었습니다. 판정할 때는 THK_nm에서 0.60을 뺀 값을 쓰십시오.
- PC, CD_nm은 영향이 없습니다.
- 원인: 기준 시편 교체 후 보정값 미반영. 10/14 18:00 재보정 완료.
"""
    tokuchae = f"""# 특채(조건부 출하) 처리 메모
작성: 품질보증팀 / 2026-10-16 17:30

- {KEY['G']['id']}: 고객사 기술팀 협의 완료. 특채 승인 (승인자: 품질팀장)
- {KEY['X']['id']}: 출하 일정 확보를 위해 선승인. 특채 승인 (승인자: 품질팀장)
- {KEY['H']['id']}: 특채 요청 → 반려. CD 이탈 폭이 고객 허용 범위 밖
- {ddr[0]['id']}: DDR5-X2 개발 로트. 특채 대상 아님
"""
    minutes = """# 품질 주간회의록 (2026-10-15)
참석: 품질보증팀, 계측기술팀, 생산관리팀

1. 파티클 기준 완화 검토
   - 고객사가 파티클 25개까지 허용할 수 있다는 의견. 11월 고객 협의 뒤 결정하기로 함. 현재 기준은 그대로.
2. MT-03 막두께 이상
   - 10/13부터 MT-03 THK가 높게 나온다는 제보. 계측기술팀이 원인 확인 중. 공지는 확인 후 따로 배포.
3. 이번 주 출하 회의
   - 10/16(금) 17시. 로트별 판정표와 출하 가능 비율을 가져온다.
4. 기타
   - 육안 검사에서 스크래치 의심 소견이 나오면 비고란에 적는다. 판정 반영 여부는 기준서를 따른다.
"""
    rm_rows = sorted(remeasure, key=lambda r: r[6])
    f_rm = csv_text(["lot_id", "wafer", "product", "항목", "원측정값", "재측정값", "재측정_시각", "사유"],
                    [(a, b, c, d, f2(e) if d != "PC" else e, f2(f) if d != "PC" else f, g.strftime("%Y-%m-%d %H:%M"), h) for a, b, c, d, e, f, g, h in rm_rows])

    files.append({"name": "판정기준_v3.md", "kind": "doc", "text": std_v3})
    files.append({"name": "판정기준_v2.md", "kind": "doc", "text": std_v2})
    files.append({"name": "MT-03_보정공지.md", "kind": "doc", "text": notice})
    files.append({"name": "재측정_기록.csv", "kind": "csv", "text": f_rm})
    files.append({"name": "특채_승인메모.md", "kind": "doc", "text": tokuchae})
    files.append({"name": "주간회의록_1015.md", "kind": "doc", "text": minutes})
    files.append({"name": "검사결과_1009.csv", "kind": "csv", "text": day_file(prev)})
    for d in (12, 13, 14, 15, 16):
        files.append({"name": f"검사결과_10{d}.csv", "kind": "csv", "text": day_file([L for L in lots if L["day"] == d])})

    return {
        "R": R, "lots": lots, "KEY": KEY, "ddr": ddr, "res": res, "hold": hold, "n_lots": n_lots, "n_badw": n_badw,
        "approved": approved, "rejected": rejected, "no_ship": no_ship, "ship_ratio": ship_ratio, "changed": changed,
        "files": files, "remeasure": remeasure, "trap_q1": trap_q1, "trap_q4": trap_q4, "f2": f2,
    }
