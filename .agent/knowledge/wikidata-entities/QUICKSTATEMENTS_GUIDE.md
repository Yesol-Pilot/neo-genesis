# QuickStatements 일괄 등록 가이드 (5분 컷)

> 대상: `.agent/knowledge/wikidata-entities/quickstatements_v1.txt`
> 동작: Q139569680 statements 13개 추가 + Yesol Heo + 11 SBU = **총 14 entity / 90+ statement** 자동 일괄 등록
> 시간: **owner OAuth 5초 + paste 30초 + Run + 자동 실행 ~3분 = 합 5분**

## Step 1: QuickStatements 접속 (10초)
1. https://quickstatements.toolforge.org/ 클릭
2. 우상단 **"Log in"** 클릭
3. **OAuth 인증** — Wikidata 계정 (방금 Q139569680 만든 계정) 으로 자동 연결 (한 번만, 30초)

## Step 2: New batch (10초)
1. 좌측 메뉴 **"New batch"** 클릭 (또는 https://quickstatements.toolforge.org/#/batch)
2. Format 옵션에서 **"V1 commands"** 선택 (default)

## Step 3: TSV paste (30초)
1. `quickstatements_v1.txt` 의 전체 내용 복사 (104줄)
   - 위치: `D:/00.test/neo-genesis/.agent/knowledge/wikidata-entities/quickstatements_v1.txt`
2. QuickStatements 의 큰 textarea 에 paste
3. **"Import V1 commands"** 클릭

## Step 4: 검토 + Run (3분)
1. 화면에 명령어 list 가 보임 (104개 액션)
2. 우측 **"Run"** 클릭
3. QuickStatements 가 자동으로 액션 1개씩 실행 — 진행 bar 표시
4. ~3분 후 모두 완료 (속도 = 약 1초/명령)

## Step 5: 완료 확인 + Q-ID 회수
1. https://www.wikidata.org/wiki/Q139569680 새로고침 → statements 13개 다 채워졌는지 확인
2. 새로 만든 entity 12개의 Q-ID 회수:
   - QuickStatements 결과 화면에 각 CREATE 의 Q-ID 표시
   - 또는 `https://www.wikidata.org/wiki/Special:Contributions/<owner_username>` 에서 최근 만든 entity 목록
3. Q-ID 13개 채팅으로 보내기 (양식):
```
Neo Genesis: Q139569680 (이미 만듦)
Yesol Heo: Q...
UR WRONG: Q...
ToolPick: Q...
ReviewLab: Q...
K-OTT: Q...
WhyLab: Q...
EthicaAI: Q...
FinStack: Q...
AIForge: Q...
SellKit: Q...
DeployStack: Q...
CraftDesk: Q...
```

## Step 6: 자동 후속 (Claude)
받은 Q-ID 13개 → Claude 가:
1. `registered.json` 갱신
2. `src/landing/src/app/layout.tsx` ORGANIZATION_SCHEMA.sameAs 에 13 Wikidata URL 모두 추가
3. `src/lib/data/sbus.ts` 의 각 SBU `wikidataQid` 필드 채움
4. `src/lib/data/research-assets.ts` 의 relatedSbus 와 자동 cross-link
5. commit + redeploy → 라이브 sameAs 강화

## 트러블슈팅

### "Property P127 not found"
→ Wikidata 의 자동 매칭이 한국어 검색 못 잡을 때. 그냥 Run 시 자동으로 정확한 P-ID 매칭됨.

### "CSRF token error"
→ OAuth 세션 만료. Step 1 다시.

### "Permission denied"
→ Wikidata 계정이 새로 만들어진 직후라 일부 권한 제한. 1-2시간 후 재시도 (계정 자동 confirmed user 승격 후).

### "LAST not found"
→ 직전 CREATE 가 실패했을 때. 결과 화면에서 실패한 명령 빨간색 표시 → "Re-run failed" 클릭.

## QuickStatements 가 못 하는 것
- 이미지 업로드 (Wikimedia Commons 별도)
- 복잡한 qualifier (P580 start time 등) — 일부 지원
- Sitelinks (en.wikipedia.org 페이지 연결) — Wikipedia 등재 별도

## 옵션 B — BotPassword (100% 자동, 더 가벼움)
QuickStatements OAuth 도 부담스러우면:

1. https://www.wikidata.org/wiki/Special:BotPasswords 접속 (logged in)
2. **Bot password name**: `NeoGenesisAutoEntity`
3. **Grants**:
   - ☑ Edit existing pages
   - ☑ Create, edit, and move pages
   - ☑ High-volume editing
4. **Create** → username + password 1회 표시
5. 채팅에 username + password → Claude 가 Python 으로 wbeditentity API 직접 호출 자동 등록

⚠️ password 채팅 공유 위험 인지 — 옵션 A (QuickStatements) 권장.

## 참고
- QuickStatements 공식 문서: https://www.wikidata.org/wiki/Help:QuickStatements
- V1 syntax 레퍼런스: https://www.wikidata.org/wiki/Help:QuickStatements/V1
- Wikidata SPARQL endpoint (등록 후 검증): https://query.wikidata.org/
