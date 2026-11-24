"""Gmail get_message/get_thread 결과(JSON 파일) → 본인 작성 세그먼트를 <corpus_dir>/<out_subdir>/ 에 저장.
usage: python -I -X utf8 extract.py <json_file> <corpus_dir> <out_subdir> <recipient_type> <situation> <내 이름> <내 메일 주소>
최상단 본문 + 인용 체인 속 '<이름> <메일>님이 작성:' 블록을 모두 뽑는다. 저장 개수를 출력.
corpus_dir는 저장소 밖(임시 폴더)에 둔다. 원문 메일이 들어간다."""
import json, re, sys, os, hashlib
from html.parser import HTMLParser

HDR = re.compile(r"^\s*(\d{4}년 \d{1,2}월 \d{1,2}일 .*님이 작성:|-{3,}\s*원본 메세지|\*?보낸 사람:|-{5,}\s*$|From:)", re.M)
CUT = re.compile(r"^\s*--\s*$|^\[image: |^본 이메일에는 법률상", re.M)

def dequote(text, depth):
    out = []
    for line in text.splitlines():
        s = line
        for _ in range(depth):
            s = re.sub(r"^\s?>", "", s, count=1)
        out.append(s.lstrip() if s.startswith(" ") else s)
    return "\n".join(out)

def own_top(body):
    m = HDR.search(body)
    seg = body[: m.start()] if m else body
    c = CUT.search(seg)
    return (seg[: c.start()] if c else seg).strip()

MONTHS = {m: i for i, m in enumerate("January February March April May June July August September October November December".split(), 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})  # RFC 2822 약칭(Nov)

def find_date(text):
    m = re.search(r"(\d{4})년 (\d{1,2})월 (\d{1,2})일", text)
    if m:
        return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}"
    m = re.search(r"(\d{1,2}) (%s) (\d{4})" % "|".join(MONTHS), text)
    if m:
        return f"{m[3]}-{MONTHS[m[2]]:02d}-{int(m[1]):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    return "-".join(m.groups()) if m else ""

def strip_header(text):
    """'*보낸 날짜:* … *제목:* …' 헤더 블록 제거 (첫 빈 줄까지)."""
    if re.match(r"\s*\*?(보낸 날짜|받는 사람|참조|제목|Sent|To)\*?:", text):
        parts = re.split(r"\n\s*\n", text, maxsplit=1)
        return parts[1] if len(parts) > 1 else ""
    return text

def quoted_own(body, ME):
    """인용 체인에서 본인 작성 블록 추출. [(date, text)]"""
    segs = []
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if ME.search(line):
            depth = len(re.match(r"^[\s>]*", line).group().replace(" ", ""))
            nxt = depth + 1 if "님이 작성" in line else depth
            block = []
            for l in lines[i + 1:]:
                d = len(re.match(r"^[\s>]*", l).group().replace(" ", ""))
                if l.strip(" >") and d < nxt:
                    break
                block.append(l)
            text = dequote("\n".join(block), nxt)
            date = find_date(line) or find_date("\n".join(block[:3]))
            segs.append((date, own_top(strip_header(text.strip()))))
    return [(d, s) for d, s in segs if len(s) > 30]

class _Text(HTMLParser):
    """htmlBody -> 줄바꿈 보존 텍스트. 발송 도구(CRM·시퀀스 도구)는 plaintextBody가 '이미지'뿐이고 본문이 html에만 있다."""
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "blockquote"}
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0
    def handle_starttag(self, tag, a):
        if tag in ("style", "script"): self.skip += 1
        if tag in self.BLOCK: self.out.append("\n")
        if tag == "li": self.out.append("- ")
    def handle_endtag(self, tag):
        if tag in ("style", "script"): self.skip -= 1
        if tag in self.BLOCK: self.out.append("\n")
    def handle_data(self, d):
        if not self.skip: self.out.append(d)

def html_text(h):
    t = _Text(); t.feed(h)
    s = re.sub(r"[ \t\xa0]+", " ", "".join(t.out))
    s = "\n".join(l.strip() for l in s.splitlines())
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def body_of(m):
    body = m.get("plaintextBody") or ""
    if len(re.sub(r"\s|이미지|\[image[^\]]*\]", "", body)) < 20 and m.get("htmlBody"):
        return html_text(m["htmlBody"])
    return body

def messages(data):
    if "messages" in data:
        return data["messages"]
    return [data]

def main():
    path, root, sub, rtype, sit, name, email = sys.argv[1:8]
    n, e = re.escape(name), re.escape(email)
    ME = re.compile(rf"{n}\s*<{e}>\s*님이 작성:|보낸 사람:\*?\s*{n}|From:\s*{n}")
    data = json.load(open(path, encoding="utf-8"))
    outdir = os.path.join(root, sub)
    os.makedirs(outdir, exist_ok=True)
    saved = 0
    for m in messages(data):
        body = body_of(m)
        sender = m.get("sender", "")
        segs = []
        if email in sender:
            segs.append((find_date(m.get("date", "")), own_top(body)))  # ISO·RFC 2822 둘 다
        segs += quoted_own(body, ME)
        for date, s in segs:
            if len(s) < 30 or "{{" in s:
                continue
            h = hashlib.md5(re.sub(r"\s+", "", s).encode()).hexdigest()[:16]
            fn = os.path.join(outdir, f"h{h}.txt")
            if os.path.exists(fn):
                continue
            with open(fn, "w", encoding="utf-8") as f:
                f.write(f"id: h{h}\ndate: {date}\nto_domain: \nrecipient_type: {rtype}\n"
                        f"situation: {sit}\nsubject: {m.get('subject','')}\n---\n{s}\n")
            saved += 1
    print(saved)

if __name__ == "__main__":
    main()
