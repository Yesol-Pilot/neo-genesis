# Wikidata 14 Entity 자동 등록 스크립트

> QuickStatements 의 autoconfirmed (4일 + 50 edit) 우회.
> BotPassword 인증 → wbeditentity API 직접 호출 → 새 계정도 가능.

## 1. BotPassword 발급 (3분)

1. https://www.wikidata.org/wiki/Special:BotPasswords 접속 (logged in)
2. **Bot password name**: `NeoGenesisRegister`
3. **Grants** 체크:
   - ☑ Basic rights
   - ☑ High-volume editing (있으면)
   - ☑ Edit existing pages
   - ☑ Create, edit, and move pages
4. **Create** 클릭 → **username + 16자 password 1회 표시** (페이지 떠나면 다시 못 봄)
5. 안전한 곳에 저장

## 2. 환경변수 설정

방법 A — `.env.local` 파일 (권장):
```bash
# D:/00.test/neo-genesis/.env.local 또는
# D:/00.test/neo-genesis/scripts/wikidata_register/.env

WIKIDATA_USERNAME=YourWikidataUser@NeoGenesisRegister
WIKIDATA_PASSWORD=abcdef1234567890abcdef
```

방법 B — Windows PowerShell 환경변수:
```powershell
$env:WIKIDATA_USERNAME = "YourWikidataUser@NeoGenesisRegister"
$env:WIKIDATA_PASSWORD = "abcdef1234567890abcdef"
```

## 3. 의존성 (이미 있으면 skip)

```bash
# Python 3.8+ 만 있으면 OK (urllib 표준 라이브러리만 사용)
python --version
```

## 4. 실행

```bash
cd D:/00.test/neo-genesis

# Dry-run (실제 등록 없이 payload 만 출력)
python scripts/wikidata_register/register_entities.py --dry-run

# 실제 등록 (모든 14 entity)
python scripts/wikidata_register/register_entities.py

# 특정 entity 만 (인덱스 1=NeoGenesis 보강, 2=Yesol Heo, 3-13=11 SBU)
python scripts/wikidata_register/register_entities.py --only=1,2

# Q139569680 보강 건너뛰고 신규만
python scripts/wikidata_register/register_entities.py --skip-existing

# Throttle 조정 (default 8s, 새 계정 안전치)
python scripts/wikidata_register/register_entities.py --throttle=15
```

## 5. 진행 + 결과

```
[auth] Using BotPassword for YourWikidataUser
[auth] Logging in...
[auth] OK. CSRF token acquired.

[01/14] Neo Genesis (existing) (edit_existing)
  ✓ Q139569680
  …throttle 8s (rate limit safe)

[02/14] Yesol Heo (founder) (create_new)
  ✓ Q139570123
  …throttle 8s

[03/14] UR WRONG (create_new)
  ✓ Q139570124
  ...
```

진행 중 `result.json` 자동 갱신 (중간 실패해도 진행분 보존):

```json
{
  "Q139569680": { "qid": "Q139569680", "url": "...", "registered_at": "2026-04-27" },
  "yesol_heo": { "qid": "Q139570123", "url": "...", "registered_at": "2026-04-27" },
  "ur_wrong": { "qid": "Q139570124", ... },
  ...
}
```

## 6. 완료 후 Claude 에게

result.json 내용 또는 핵심 Q-ID 매핑 채팅으로 보내기 → Claude 가:
1. `.agent/knowledge/wikidata-entities/registered.json` 갱신
2. `src/landing/src/app/layout.tsx` ORGANIZATION_SCHEMA.sameAs 에 13 Wikidata URL 추가
3. `src/lib/data/sbus.ts` 의 각 SBU `wikidataQid` 자동 매핑
4. commit + redeploy

## 트러블슈팅

### "Login failed"
- BotPassword username 형식 확인: `YourWikidataUser@NeoGenesisRegister` (메인 username + @ + bot password name)
- password 띄어쓰기 / 따옴표 제거

### "ratelimited" 에러
- 새 계정은 시간당 ~8 edit 제한
- `--throttle=15` 또는 `--throttle=30` 으로 늘림
- 또는 `--only=1,2,3` 으로 일부만 먼저 실행 → 1시간 후 나머지

### "permissiondenied" 에러
- BotPassword grants 누락. Special:BotPasswords 에서 권한 추가
- 특히 "Create, edit, and move pages" 필수

### 재실행 안전성
- result.json 에 진행분 자동 저장
- 중간 실패 시 다시 실행하면 이어서 (단, 이미 등록한 entity 의 중복 등록 방지 안 됨 — `--only` 로 잔여만 재실행)

## 보안

- BotPassword 는 **revoke 가능**: https://www.wikidata.org/wiki/Special:BotPasswords 에서 NeoGenesisRegister 삭제
- 1회 사용 후 즉시 revoke 권장
- `.env.local` 파일은 `.gitignore` 에 이미 등록 → commit 안 됨 (확인: `git status` 하면 .env.local 표시 안 됨)
