#!/usr/bin/env python3
"""tasks.js의 파일 텍스트만 읽어서 정답을 다시 계산해 본다 (생성기와 독립 검산)."""
import csv, io, json, math, datetime as dt
from collections import defaultdict
from pathlib import Path

s = (Path(__file__).resolve().parent.parent / "assets/data/tasks.js").read_text(encoding="utf-8")
tasks = json.loads(s[s.index("["): s.rindex("]") + 1])
T = {t["id"]: t for t in tasks}
def f(t, name): return next(x["text"] for x in T[t]["files"] if x["name"] == name)
def rows(text): return list(csv.DictReader(io.StringIO(text)))
def rhu(x, nd=0): q = 10 ** nd; return math.floor(x * q + 0.5) / q
ok = True
def check(qid, got):
    global ok
    q = next(q for t in tasks for q in t["questions"] if q["id"] == qid)
    exp = q["answer"] if q["type"] != "mc" else q["options"][q["answer"]]
    good = str(got) == str(exp)
    ok &= good
    print(("OK " if good else "XX ") + qid, "expected", exp, "| recomputed", got)

# T1
log = rows(f("T1", "alarm_log_2026-09.csv"))
master = {r["equip_id"]: int(r["planned_hours"]) for r in rows(f("T1", "equipment_master.csv"))}
P = lambda x: dt.datetime.strptime(x, "%Y-%m-%d %H:%M")
v = [r for r in log if dt.datetime(2026,9,1) <= P(r["occurred_at"]) <= dt.datetime(2026,9,30,23,59) and r["alarm_code"] != "P900"]
check("T1Q1", len(v))
crit = defaultdict(int)
for r in v:
    if r["severity"] == "Critical": crit[r["equip_id"]] += int(r["downtime_min"])
check("T1Q2", max(crit, key=crit.get))
by = defaultdict(list)
for r in v: by[(r["equip_id"], r["alarm_code"])].append(P(r["occurred_at"]))
rec = sorted(f"{e}:{c}" for (e, c), ts in by.items() if any(sorted(ts)[i+2]-sorted(ts)[i] <= dt.timedelta(hours=24) for i in range(len(ts)-2)))
check("T1Q3", ", ".join(rec))
av = {e: (master[e]*60 - crit[e]) / (master[e]*60) * 100 for e in master}
check("T1Q4", f"{rhu(min(av.values()), 1):.1f}")

# T2
raw = rows(f("T2", "survey_raw.csv"))
latest = {}
for r in raw:
    if r["resp_id"] not in latest or r["submitted_at"] > latest[r["resp_id"]]["submitted_at"]: latest[r["resp_id"]] = r
check("T2Q1", len(latest))
recs = [int(r["recommend"]) for r in latest.values() if r["recommend"] != ""]
idx = (sum(x >= 9 for x in recs) - sum(x <= 6 for x in recs)) / len(recs) * 100
check("T2Q2", int(rhu(idx)))
sat, n = {}, defaultdict(int)
for r in latest.values():
    n[r["dept"]] += 1
    vals = [int(r[k]) for k in ("q1","q2","q3","q4","q5") if r[k] not in ("",) and 1 <= int(r[k]) <= 5]
    if len(vals) >= 3: sat[r["resp_id"]] = (r["dept"], sum(vals)/len(vals))
ds = defaultdict(list)
for d, x in sat.values(): ds[d].append(x)
elig = {d: sum(x)/len(x) for d, x in ds.items() if n[d] >= 8}
check("T2Q3", max(elig, key=elig.get))
excl = len(latest) - len(sat)
check("T2Q4", "유효 문항이 3개 미만이라 만족도 계산에서 빠지는 응답자는 2명이다." if excl == 2 else f"excluded={excl}")

# T3
clubs = sorted({x["name"].split("/")[0] for x in T["T3"]["files"] if "/" in x["name"]})
allrec, members, joined = [], {}, {}
for c in clubs:
    for r in rows(f("T3", f"{c}/영수증.csv")): r["club"] = c; allrec.append(r)
    for r in rows(f("T3", f"{c}/회원명단.csv")): members[(c, r["member_id"])] = r
    for r in rows(f("T3", f"{c}/가입일.csv")): joined[(c, r["member_id"])] = dt.date.fromisoformat(r["가입일"])
cnt = defaultdict(int)
for r in allrec: cnt[r["receipt_no"]] += 1
bad, young, tot = set(), 0, defaultdict(int)
for r in allrec:
    d = dt.date.fromisoformat(r["use_date"]); m = members[(r["club"], r["member_id"])]
    reasons = []
    if not (dt.date(2026,7,1) <= d <= dt.date(2026,9,30)): reasons.append(1)
    if (d - joined[(r["club"], r["member_id"])]).days < 30: reasons.append(2); young += 1
    if m["재직상태"] == "퇴사" and m["퇴사일"] and d > dt.date.fromisoformat(m["퇴사일"]): reasons.append(3)
    if r["category"] in ("주류", "상품권"): reasons.append(4)
    if cnt[r["receipt_no"]] >= 2: reasons.append(5)
    if reasons: bad.add(r["receipt_no"]); continue
    tot[r["club"]] += min(int(r["amount"]), 50000)
check("T3Q1", ", ".join(sorted(bad)))
check("T3Q2", young)
check("T3Q3", ", ".join(c for c in ["등산","풋살","밴드"] if tot[c] > 300000) or "없음")
check("T3Q4", sum(min(v, 300000) for v in tot.values()))

# T4
lic = rows(f("T4", "licenses.csv"))
price = {"DocsAI": {"Business": 18000, "Pro": 9000}, "DesignHub": {"Business": 32000, "Pro": 16000}, "CodePilot": {"Business": 25000, "Pro": 12000}}
base = dt.date(2026, 9, 30)
keep = [r for r in lic if (base - dt.date.fromisoformat(r["last_login"])).days <= 60]
check("T4Q1", len(lic) - len(keep))
after = []
for r in keep:
    p = r["plan"]
    if p == "Business" and int(r["active_days_30d"]) <= 5 and not (r["tool"] == "CodePilot" and r["dept"] == "개발"): p = "Pro"
    after.append((r["tool"], p))
check("T4Q2", sum(price[t][p] for t, p in after))
seats = defaultdict(int)
for t, _ in after: seats[t] += 1
check("T4Q3", sum(round(price[t][p] * (0.8 if seats[t] >= 10 else 1)) for t, p in after))
check("T4Q4", ", ".join(t for t in price if seats[t] < 10))
print("ALL OK" if ok else "MISMATCH")
