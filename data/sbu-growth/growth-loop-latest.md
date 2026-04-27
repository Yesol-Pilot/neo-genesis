# SBU Growth Loop

- generatedAt: 2026-04-27T11:01:18+09:00
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
  "date": "2026-04-27",
  "results": [
    {
      "site": "aiforge",
      "action": "verify-only",
      "slug": "2026-04-27-agentic-crm-automation-tools",
      "latest": "2026-04-27",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "craftdesk",
      "action": "verify-only",
      "slug": "2026-04-27-brand-asset-workflow-software",
      "latest": "2026-04-27",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "deploystack",
      "action": "verify-only",
      "slug": "2026-04-27-devops-incident-review-tools",
      "latest": "2026-04-27",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "finstack",
      "action": "verify-only",
      "slug": "2026-04-27-banking-api-platforms",
      "latest": "2026-04-27",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "sellkit",
      "action": "verify-only",
      "slug": "2026-04-27-lifecycle-email-automation-tools",
      "latest": "2026-04-27",
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
            },
            {
              "slug": "2026-04-26-ai-sales-enablement-tools-for-ecommerce",
              "date": "2026-04-26",
              "words": 423,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "e-commerce-analytics-tools",
              "date": "2026-03-22",
              "words": 511,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "ecommerce-inventory-management-software-comparison",
              "date": "2026-02-24",
              "words": 432,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "best-ecommerce-platform-for-dropshipping-2026",
              "date": "2026-02-23",
              "words": 0,
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
  "generatedAt": "2026-04-27T11:01:14+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 0,
  "issues": [],
  "warnings": []
}
```

