// UserPromptSubmit 훅: 메일·업무 문서·대외 문구 요청이면 b2b-tone-manner 스킬을 먼저 로드하라고 끼워 넣는다.
// ponytail: 키워드 정규식이라 오탐("UI 문구")이 있을 수 있다. 오탐은 주입 문구 안에서 Claude가 걸러낸다.
import { readFileSync } from 'node:fs';

const TRIGGER = /메일|회신|답장|콜드|팔로업|follow-?up|고객사|담당자님|견적|제안서|소개서|사업계획서|입찰|공문|슬랙|카톡|안내 ?메시지|공지문|안내문|문구|기획안|회의자료|협의\(안\)|보고서|슬라이드|장표|포트폴리오|회고|상세페이지|노션|톤앤?매너|말투|번역투|AI\s?티/i;

let prompt = '';
try {
  prompt = JSON.parse(readFileSync(0, 'utf8')).prompt ?? '';
} catch {
  process.exit(0);
}

if (TRIGGER.test(prompt)) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext:
        '이 요청이 고객사·기관·파트너·벤더에게 보내는 메일·메시지, 또는 기획안·회의자료·제안서·보고·슬라이드·포트폴리오 같은 업무 문서를 쓰거나 고치는 일이면, ' +
        '작성 전에 b2b-tone-manner 스킬을 먼저 로드해 그 규칙과 자기검수 체크리스트를 적용한다. ' +
        '코드 속 UI 문구처럼 대외 커뮤니케이션이 아니면 무시한다.',
    },
  }));
}
