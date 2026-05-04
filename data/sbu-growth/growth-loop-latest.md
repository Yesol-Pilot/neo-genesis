# SBU Growth Loop

- generatedAt: 2026-05-04T17:45:28+09:00
- passed: true

## Steps

| Step | OK | Status |
|---|---:|---:|
| control-tower | true | 0 |
| search-growth-flywheel | true | 0 |
| full-live-quality | true | 0 |
| regression-gate | true | 0 |

## Tails

### control-tower

```text
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
      "actions": [
        "Review dirty working tree before automated publish/deploy."
      ]
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

### full-live-quality

```text
passed=True passedCount=13/13
```

### regression-gate

```text
{
  "report": "data\\sbu-growth\\control-tower-latest.json",
  "generatedAt": "2026-05-04T17:43:13+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 6,
  "issues": [],
  "warnings": [
    {
      "site": "toolpick",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    },
    {
      "site": "aiforge",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    },
    {
      "site": "craftdesk",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    },
    {
      "site": "deploystack",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    },
    {
      "site": "finstack",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    },
    {
      "site": "sellkit",
      "code": "dirty_worktree",
      "message": "SBU working tree has uncommitted changes; skip automated deploy until reviewed."
    }
  ]
}
```

