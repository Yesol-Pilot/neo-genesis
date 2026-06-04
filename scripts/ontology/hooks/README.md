# `scripts/ontology/hooks/` — External Event → ActionRun Adapters

> v0.3 박제 (2026-05-14). PROV-O Activity 패턴 정합.

외부 시스템 (PM2, Vercel, Killswitch, GitHub Actions 등) 의 이벤트를 ontology ActionRun 으로 변환하는 adapter 들. 각 hook 은 `auto_record.record_action()` 을 호출하여 nodes.jsonl 에 fast-path append.

## Hook 목록

| Hook | kind | 호출 시점 |
|---|---|---|
| `killswitch_hook.py` | `killswitch_fire` | quant-bot HaltOrchestrator 발동 시, 또는 안전 정책 위반 |
| `deploy_hook.py` | `deploy` | Vercel / PM2 / GitHub Actions / manual deploy 완료 시 |

dispatcher 의 self-record (`scripts/persona/dispatcher.py` 통합) 는 별도 — 매 `--query` 호출 시 자동 박제.

## Wiring 예시

### Killswitch (quant-bot HaltOrchestrator)
`auto-trading/src/core/kill-switch-runtime.js` 에서 6-step 의 마지막 (`sendAlert`) 다음에:

```javascript
// Step 7: Ontology audit trail
const { spawn } = require('child_process');
spawn('python', [
  'scripts/ontology/hooks/killswitch_hook.py',
  '--layer', layer,
  '--trigger', triggerReason,
  '--affected', 'neo://service/ysh-server/quant-bot-live',
  '--details', JSON.stringify(context),
], { detached: true, stdio: 'ignore' });
```

### Vercel Deploy
GitHub Actions workflow (`.github/workflows/deploy.yml`) 의 deploy step 다음에:

```yaml
- name: Record deploy in ontology
  run: |
    python scripts/ontology/hooks/deploy_hook.py \
      --service "neo://service/vercel-edge/${{ matrix.sbu }}" \
      --commit "${{ github.sha }}" \
      --result success \
      --platform vercel \
      --duration-sec ${{ env.DEPLOY_DURATION }}
```

### PM2 restart
`ecosystem.config.js` 의 process 정의 안:

```javascript
{
  name: 'quant-bot-live',
  script: 'src/v6-live-runner.js',
  post_start: 'python scripts/ontology/hooks/deploy_hook.py --service neo://service/ysh-server/quant-bot-live --commit $(git rev-parse HEAD) --platform pm2',
}
```

## 보안

- Personal 절대 금지 — hook 의 `--details` 에 `personal/` path 또는 secret 전달 금지
- secret pattern 은 `auto_record.py` 내부 검증 없음 — caller 책임 (외부 hook 에서 redact)
- `auto_record` 의 idempotent SHA ID 가 동일 이벤트 재기록 방지

## 다음 단계

- v0.4 에서 cloudflare worker / mac-build 등 fleet 의 다른 디바이스 deploy hook 추가
- `dispatcher_route` 가 가장 high-volume — 24h audit log compaction 필요 가능 (event sourcing)
