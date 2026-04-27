# SBU Growth Loop

- generatedAt: 2026-04-27T13:01:34+09:00
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
            "slug": "2026-04-27-lifecycle-email-automation-tools",
            "file": "src\\sbu\\sellkit\\content\\blog\\2026-04-27-lifecycle-email-automation-tools.mdx",
            "title": "Lifecycle Email Automation Tools for Lean Ecommerce Teams in 2026",
            "date": "2026-04-27",
            "description": "lifecycle email automation tools - A practical evaluation guide for ecommerce growth, sales enablement, marketing automation, and conversion tools.",
            "category": "Sales Tools",
            "draft": false,
            "words": 1046,
            "completeFrontmatter": true,
            "hasCta": true,
            "hasInternalLink": true,
            "hasExternalLink": false,
            "ready": true
          },
          "daysSinceLatest": 0,
          "fresh": true,
          "categoryCount": 10,
          "avgWords": 1033,
          "frontmatterCoverage": 1,
          "ctaCoverage": 0.873,
          "internalLinkCoverage": 0.766,
          "weakSamples": [
            {
              "slug": "best-ecommerce-platform-for-dropshipping-2026",
              "date": "2026-02-23",
              "words": 462,
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
  "generatedAt": "2026-04-27T13:01:33+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 0,
  "issues": [],
  "warnings": []
}
```

