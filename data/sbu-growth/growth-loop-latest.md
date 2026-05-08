# SBU Growth Loop

- generatedAt: 2026-05-08T09:51:10+09:00
- passed: false

## Steps

| Step | OK | Status |
|---|---:|---:|
| publisher-verify | true | 0 |
| control-tower | true | 0 |
| search-growth-flywheel | true | 0 |
| full-live-quality | false | 1 |
| regression-gate | true | 0 |

## Tails

### publisher-verify

```text
{
  "date": "2026-05-08",
  "results": [
    {
      "site": "aiforge",
      "action": "verify-only",
      "slug": "2026-05-08-ai-agent-evaluation-platforms",
      "latest": "2026-05-08",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "craftdesk",
      "action": "verify-only",
      "slug": "2026-05-08-ai-design-qa-tools",
      "latest": "2026-05-08",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "deploystack",
      "action": "verify-only",
      "slug": "2026-05-08-deployment-preview-workflows",
      "latest": "2026-05-08",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "finstack",
      "action": "verify-only",
      "slug": "2026-05-08-payment-reconciliation-tools",
      "latest": "2026-05-08",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "sellkit",
      "action": "verify-only",
      "slug": "2026-05-08-ecommerce-conversion-analytics-tools",
      "latest": "2026-05-08",
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
              "slug": "2026-05-07-lifecycle-email-automation-tools",
              "date": "2026-05-07",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-06-customer-review-mining-tools",
              "date": "2026-05-06",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-05-ai-product-description-tools",
              "date": "2026-05-05",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-04-ecommerce-conversion-analytics-tools",
              "date": "2026-05-04",
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
      "actions": [
        "Review dirty working tree before automated publish/deploy."
      ]
    }
  ]
}
```

### search-growth-flywheel

```text
        "expectedLiveCoverage": {
          "slug": "2026-05-08-ecommerce-conversion-analytics-tools",
          "title": "Ecommerce Conversion Analytics Tools for 2026 in 2026",
          "blogUrl": "https://sellkit.neogenesis.app/blog",
          "detailUrl": "https://sellkit.neogenesis.app/blog/2026-05-08-ecommerce-conversion-analytics-tools",
          "sitemapUrl": "https://sellkit.neogenesis.app/sitemap.xml"
        },
        "liveCoverageMissing": [],
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
  "failureSummary": {
    "passed": true,
    "gscOpportunityTotal": 83,
    "pipelinePassed": true,
    "liveCoverageMissingCount": 0,
    "liveCoverageMissing": [],
    "failingSites": []
  },
  "passed": true,
  "output": {
    "stampedJson": "data\\sbu-growth\\search-growth-flywheel-2026-05-08T09-49-22-09-00.json",
    "stampedMd": "data\\sbu-growth\\search-growth-flywheel-2026-05-08T09-49-22-09-00.md",
    "latestJson": "data\\sbu-growth\\search-growth-flywheel-latest.json",
    "latestMd": "data\\sbu-growth\\search-growth-flywheel-latest.md",
    "writesDefaultLatest": true,
    "written": [
      "data\\sbu-growth\\search-growth-flywheel-2026-05-08T09-49-22-09-00.json",
      "data\\sbu-growth\\search-growth-flywheel-2026-05-08T09-49-22-09-00.md",
      "data\\sbu-growth\\search-growth-flywheel-latest.json",
      "data\\sbu-growth\\search-growth-flywheel-latest.md"
    ]
  }
}
```

### full-live-quality

```text
passed=False passedCount=12/13
```

### regression-gate

```text
{
  "report": "data\\sbu-growth\\control-tower-latest.json",
  "generatedAt": "2026-05-08T09:48:39+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 1,
  "issues": [],
  "warnings": [
    {
      "site": "sellkit",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    }
  ]
}
```

