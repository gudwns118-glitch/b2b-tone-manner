"""말투 정량 분석: <corpus_dir>/*/*.txt → 빈도 리포트 (stdout).
usage: python -X utf8 analyze.py <corpus_dir>"""
import re, sys, glob, os
from collections import Counter, defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "corpus"

def load():
    docs, seen = [], set()
    for f in glob.glob(os.path.join(ROOT, "*", "*.txt")):
        if os.path.basename(os.path.dirname(f)).startswith("_") or os.path.basename(os.path.dirname(f)) == "docs":  # docs/는 analyze_docs.py 몫
            continue
        raw = open(f, encoding="utf-8").read()
        head, _, body = raw.partition("\n---\n")
        meta = dict(l.split(": ", 1) for l in head.splitlines() if ": " in l)
        body = body.strip()
        key = re.sub(r"\s+", "", body)[:300]  # 같은 메일이 인용·원본으로 중복 수집되는 것 제거
        if not body or key in seen or "{{" in body:
            continue
        seen.add(key)
        meta["body"] = body
        meta["period"] = os.path.basename(os.path.dirname(f))
        docs.append(meta)
    # 긴 스레드 하나가 결과를 지배하지 않도록 제목(스레드)당 상한
    CAP = 15
    per_thread, capped = Counter(), []
    for d in sorted(docs, key=lambda d: d.get("date", "")):
        t = re.sub(r"^((re|fw|fwd)\s*:\s*)+", "", d.get("subject", "").strip(), flags=re.I)[:40]
        per_thread[t] += 1
        if per_thread[t] <= CAP:
            capped.append(d)
    print(f"# 중복 제거 후 {len(docs)}통, 스레드 상한({CAP}) 적용 후 {len(capped)}통, 스레드 수 {len(per_thread)}")
    print("# 최다 스레드:", per_thread.most_common(5))
    return capped

# 표현 → 정규식. "쓰는 것" vs "AI가 흔히 쓰는 것" 둘 다 센다.
PHRASES = {
    # 연결어
    "추가로": r"추가로", "또한": r"또한", "아울러": r"아울러", "다만": r"다만",
    "하여(문두)": r"(^|[.!?\n]\s*)하여 ", "그래서": r"그래서", "따라서": r"따라서",
    "혹시": r"혹시", "우선": r"우선", "다름이 아니라": r"다름이 아니라",
    # 호칭
    "귀사": r"귀사", "당사": r"당사", "저희": r"저희", "양사": r"양사",
    # 어미/관용
    "~하고자": r"하고자", "~드리며": r"드리며", "~했으며/하였으며": r"(했|하였)으며",
    "~도록 하겠습니다": r"도록 하겠습니다", "~것 같습니다": r"것 같습니다",
    "~것으로 보입니다": r"것으로 보입니다", "~주신": r"(요청|문의|전달|말씀|공유|회신) 주신",
    "간단하게": r"간단하게", "편하게": r"편하게", "인지하고 있겠습니다": r"인지하고 있겠습니다",
    "여쭙": r"여쭙", "고대하겠습니다": r"고대하겠습니다", "양해 부탁": r"양해 부탁",
    "다시 한번": r"다시 한\s?번", "최선을 다하겠습니다": r"최선을 다하겠습니다",
    "~하시기 바랍니다": r"하시기 바랍니다", "주저하지": r"주저하지",
    "도움이 되": r"도움이 되", "소중한": r"소중한", "혁신": r"혁신", "최적": r"최적",
    # 마무리 상투구
    "문의 사항은 언제든 편하게": r"문의\s?사항은 언제든 편하게",
    "말씀 부탁 드리겠습니다": r"말씀 부탁 ?드리겠습니다", "말씀 주세요": r"말씀 주세요",
    # 띄어쓰기
    "전달 드(띄움)": r"전달 드", "전달드(붙임)": r"전달드",
    "부탁 드(띄움)": r"부탁 드", "부탁드(붙임)": r"부탁드",
    "감사 드(띄움)": r"감사 드", "감사드(붙임)": r"감사드",
    "문의 드(띄움)": r"문의 드", "문의드(붙임)": r"문의드",
    # 시간어
    "금일": r"금일", "차주": r"차주", "익월": r"익월", "유선": r"유선",
    # 기호
    "※": r"※", "▶": r"▶", "→": r"→", "✅": r"✅", "*굵게*": r"\*[^*\n]+\*",
    "줄표(—)": r"—", "콜론 끝(:\\n)": r":\s*\n",
}
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

def sentences(body):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 3]

def main():
    docs = load()
    n = len(docs)
    if not n:
        sys.exit(f"메일 0통: {ROOT}/<기간>/*.txt 경로를 확인하세요.")
    print(f"# 문서 수: {n}")
    for k in ("period", "recipient_type", "situation"):
        print(f"\n## {k}\n", Counter(d.get(k, "?") for d in docs).most_common())

    print("\n## 표현: 등장 메일 수 (비율) / 총 횟수")
    for name, pat in PHRASES.items():
        rx = re.compile(pat, re.M)
        hits = [len(rx.findall(d["body"])) for d in docs]
        docs_with = sum(1 for h in hits if h)
        print(f"{name:28s} {docs_with:4d} ({docs_with/n:5.1%}) / {sum(hits)}")

    print("\n## 이모지")
    em = Counter(); per_doc = Counter()
    for d in docs:
        es = EMOJI.findall(d["body"]); em.update(es); per_doc[min(len(es), 3)] += 1
    print("종류:", em.most_common(15)); print("메일당 개수(3=3+):", sorted(per_doc.items()))
    by_sit = defaultdict(lambda: [0, 0])
    for d in docs:
        by_sit[d.get("situation", "?")][0] += 1
        by_sit[d.get("situation", "?")][1] += bool(EMOJI.search(d["body"]))
    print("상황별 이모지 포함 비율:", {k: f"{v[1]}/{v[0]}" for k, v in sorted(by_sit.items())})

    print("\n## 첫 줄 (인사) 상위")
    print(Counter(re.sub(r"\S+ ?(님|님!)", "{X}님", d["body"].splitlines()[0])[:40] for d in docs).most_common(12))
    print("\n## 둘째 줄 (소속) 상위")
    print(Counter((d["body"].splitlines()[1:2] or [""])[0][:40] for d in docs).most_common(10))
    print("\n## 마지막 줄 (서명) 패턴")
    def sig(d):
        last = d["body"].strip().splitlines()[-1]
        if "팀 드림" in last: return "{팀} 드림."
        if re.search(r"\S+ 드림\.?$", last) and len(last.split()) > 2: return "{긴 서명} " + " ".join(last.split()[1:-2])
        if last.endswith("드림.") or last.endswith("드림"): return last
        return "(기타) " + last[:20]
    sigs = Counter(sig(d) for d in docs)
    print(sigs.most_common(10))
    by_type = defaultdict(Counter)
    for d in docs: by_type[d.get("recipient_type", "?")][sig(d)[:12]] += 1
    for t, c in by_type.items(): print(" ", t, c.most_common(3))
    print("\n## 맺음 '감사합니다' 형태:",
          Counter(m for d in docs for m in re.findall(r"감사합니다[.!]?", d["body"])).most_common())

    print("\n## 길이")
    lens = sorted(len(s) for d in docs for s in sentences(d["body"]))
    q = lambda p: lens[int(len(lens) * p)]
    print(f"문장 길이 중앙값 {q(.5)}, p25 {q(.25)}, p75 {q(.75)}, p90 {q(.9)}")
    bl = sorted(len(d["body"]) for d in docs)
    print(f"본문 글자수 중앙값 {bl[n//2]}, p25 {bl[n//4]}, p75 {bl[3*n//4]}")
    paras = sorted(len(sentences(p)) for d in docs for p in re.split(r"\n\s*\n", d["body"]) if p.strip())
    print("문단당 문장 수 분포:", Counter(min(p, 5) for p in paras).most_common())
    bullets = sum(1 for d in docs if re.search(r"^\s*[-•·]\s", d["body"], re.M))
    print(f"불릿 포함 메일: {bullets} ({bullets/n:.0%})")
    print("\n## 느낌표 개수/메일:", Counter(min(d['body'].count('!'), 6) for d in docs).most_common())

if __name__ == "__main__":
    main()
