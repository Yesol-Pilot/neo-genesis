# SBU Growth Loop

- generatedAt: 2026-05-04T13:54:42+09:00
- passed: true

## Steps

| Step | OK | Status |
|---|---:|---:|
| publisher-verify | true | 0 |
| control-tower | true | 0 |
| search-growth-flywheel | true | 0 |
| regression-gate | true | 0 |

## Tails

### publisher-verify

```text
{
  "date": "2026-05-04",
  "results": [
    {
      "site": "aiforge",
      "action": "verify-only",
      "slug": "2026-05-04-ai-agent-evaluation-platforms",
      "latest": "2026-05-04",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "craftdesk",
      "action": "verify-only",
      "slug": "2026-05-04-ai-design-qa-tools",
      "latest": "2026-05-04",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "deploystack",
      "action": "verify-only",
      "slug": "2026-05-04-deployment-preview-workflows",
      "latest": "2026-05-04",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "finstack",
      "action": "verify-only",
      "slug": "2026-05-04-payment-reconciliation-tools",
      "latest": "2026-05-04",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "sellkit",
      "action": "verify-only",
      "slug": "2026-05-04-ecommerce-conversion-analytics-tools",
      "latest": "2026-05-04",
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
          "daysSinceLatest": 0,
          "fresh": true,
          "categoryCount": 10,
          "avgWords": 1030,
          "frontmatterCoverage": 1,
          "ctaCoverage": 0.878,
          "internalLinkCoverage": 0.762,
          "weakSamples": [
            {
              "slug": "2026-05-04-ecommerce-conversion-analytics-tools",
              "date": "2026-05-04",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-03-lifecycle-email-automation-tools",
              "date": "2026-05-03",
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

### search-growth-flywheel

```text
            "status": 200,
            "ok": true
          },
          "sitemap": {
            "status": 200,
            "ok": true
          },
          "robots": {
            "status": 200,
            "ok": true
          },
          "cron": {
            "status": 401,
            "protected": true
          }
        },
        "indexnowSubmitScript": true,
        "gscReady": true,
        "status": "green",
        "issues": []
      },
      {
        "site": "sellkit",
        "latest": {
          "slug": "2026-05-04-ecommerce-conversion-analytics-tools",
          "title": "Ecommerce Conversion Analytics Tools for 2026 in 2026",
          "date": "2026-05-04"
        },
        "staleDays": 0,
        "live": {
          "blog": {
            "status": 200,
            "ok": true
          },
          "detail": {
            "status": 200,
            "ok": true
          },
          "sitemap": {
            "status": 200,
            "ok": true
          },
          "robots": {
            "status": 200,
            "ok": true
          },
          "cron": {
            "status": 401,
            "protected": true
          }
        },
        "indexnowSubmitScript": true,
        "gscReady": true,
        "status": "green",
        "issues": []
      }
    ]
  },
  "passed": true
}
```

### regression-gate

```text
{
  "report": "data\\sbu-growth\\control-tower-latest.json",
  "generatedAt": "2026-05-04T13:54:07+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 0,
  "issues": [],
  "warnings": []
}
```

