"""문서 문장 종결 비율: <docs_dir>/<source>/*.txt (헤더 doc_type·audience, --- 아래 본문) → 유형·독자별 집계.
usage: python -X utf8 analyze_docs.py <docs_dir>
ponytail: 마지막 어절 정규식 분류라 거칠다. 비율 감만 본다."""
import re,glob,collections,sys,os
ROOT=sys.argv[1] if len(sys.argv)>1 else "docs"
def cls(s):
    s=re.sub(r'\*\*|\[.*?\]$|[()（）\s]+$','',s).strip().rstrip('.!?~ ').strip()
    s=re.sub(r'\(.*?\)$','',s).strip().rstrip('.!? ')
    if not s or not re.search(r'[가-힣]$',s): return None
    if re.search(r'(습니다|ㅂ니다|니다)$',s): return '합니다체'
    if re.search(r'(요|죠)$',s): return '해요체'
    if re.search(r'(했다|한다|이다|있다|된다|였다|겠다)$',s): return '한다체'
    if re.search(r'(함|임|음|됨|있음|없음|필요|예정|요망|불가|가능|완료|중)$',s): return '명사형(~함/필요/예정)'
    if re.search(r'(는지|ㄴ지|은지|인지|할지|될지|나요|까요|가요)$',s): return '의문'
    return '개조식 명사/동작명사'
res=collections.defaultdict(collections.Counter)
for f in glob.glob(os.path.join(ROOT,'*','*.txt')):
    t=open(f,encoding='utf-8').read()
    hdr,sep,body=t.partition('---\n')
    dt=re.search(r'doc_type: (\S+)',hdr); au=re.search(r'audience: (\S+)',hdr)
    if not (sep and dt and au):
        print('건너뜀(헤더 doc_type·audience와 --- 필요):',f,file=sys.stderr); continue
    dt,au=dt.group(1),au.group(1)
    for line in body.splitlines():
        line=line.strip().lstrip('-*#>|0123456789.①②③④⑤⑥ ').strip()
        if len(line)<8 or line.startswith('|'): continue
        for seg in re.split(r'(?<=[.!?])\s+',line):
            c=cls(seg)
            if c: res[f'{dt}/{au}'][c]+=1; res['__'+os.path.basename(os.path.dirname(f))][c]+=1; res['ALL'][c]+=1
if not res: sys.exit(f'문서 0건: {ROOT}/<source>/*.txt 경로를 확인하세요.')
for k in sorted(res):
    tot=sum(res[k].values()); print(k,tot,{a:f'{b}({b*100//tot}%)' for a,b in res[k].most_common()})
