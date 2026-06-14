# SBU Growth Loop

- generatedAt: 2026-05-02T10:28:18+09:00
- passed: true

## Steps

| Step | OK | Status |
|---|---:|---:|
| publisher-verify | true | 0 |
| control-tower | true | 0 |
| regression-gate | true | 0 |

## Tails

### publisher-verify

```text
{
  "date": "2026-05-02",
  "results": [
    {
      "site": "aiforge",
      "action": "verify-only",
      "slug": "2026-05-02-ai-workflow-automation-stack",
      "latest": "2026-05-02",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "craftdesk",
      "action": "verify-only",
      "slug": "2026-05-02-design-system-documentation-tools",
      "latest": "2026-05-02",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "deploystack",
      "action": "verify-only",
      "slug": "2026-05-02-edge-deployment-platforms",
      "latest": "2026-05-02",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "finstack",
      "action": "verify-only",
      "slug": "2026-05-02-invoice-automation-software",
      "latest": "2026-05-02",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "sellkit",
      "action": "verify-only",
      "slug": "2026-05-02-customer-review-mining-tools",
      "latest": "2026-05-02",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    }
  ]
}
```

### control-tower

```text
          "weakSamples": [
            {
              "slug": "2026-05-02-customer-review-mining-tools",
              "date": "2026-05-02",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-01-ai-product-description-tools",
              "date": "2026-05-01",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-04-30-customer-review-mining-tools",
              "date": "2026-04-30",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-04-29-ai-product-description-tools",
              "date": "2026-04-29",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            }
          ]
        }
      },
      "live": {
        "blog": {
          "ok": true,
          "status": 200,
          "hasSlug": true,
          "hasTitle": true
        },
        "detail": {
          "ok": true,
          "status": 200,
          "hasTitle": true,
          "hasDate": true
        },
        "sitemap": {
          "ok": true,
          "status": 200,
          "hasLatestSlug": true
        },
        "robots": {
          "ok": true,
          "status": 200,
          "hasSitemap": true
        }
      },
      "actions": []
    }
  ]
}
```

### regression-gate

```text
{
  "report": "data\\sbu-growth\\control-tower-latest.json",
  "generatedAt": "2026-05-02T10:28:13+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 0,
  "issues": [],
  "warnings": []
}
```

