# SBU Growth Loop

- generatedAt: 2026-05-20T15:53:52+09:00
- passed: true

## Steps

| Step | OK | Status |
|---|---:|---:|
| publisher-verify | true | 0 |
| control-tower | true | 0 |
| search-growth-flywheel | true | 0 |
| full-live-quality | true | 0 |
| regression-gate | true | 0 |
| posthog-7d | true | 0 |
| ga4-report | true | 0 |

## Judgment Control

- ok: true
- decisionArtifact: data\sbu-growth\judgment-control-latest.json
- htmlReport: data\sbu-growth\judgment-control-latest.html

## Tails

### publisher-verify

```text
{
  "date": "2026-05-20",
  "results": [
    {
      "site": "aiforge",
      "action": "verify-only",
      "slug": "2026-05-20-ai-agent-evaluation-platforms",
      "latest": "2026-05-20",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "craftdesk",
      "action": "verify-only",
      "slug": "2026-05-20-ai-design-qa-tools",
      "latest": "2026-05-20",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "deploystack",
      "action": "verify-only",
      "slug": "2026-05-20-deployment-preview-workflows",
      "latest": "2026-05-20",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "finstack",
      "action": "verify-only",
      "slug": "2026-05-20-payment-reconciliation-tools",
      "latest": "2026-05-20",
      "live": {
        "blog": true,
        "detail": true,
        "sitemap": true
      }
    },
    {
      "site": "sellkit",
      "action": "verify-only",
      "slug": "2026-05-20-ecommerce-conversion-analytics-tools",
      "latest": "2026-05-20",
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
              "slug": "2026-05-09-ai-product-description-tools",
              "date": "2026-05-09",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
              "slug": "2026-05-08-ecommerce-conversion-analytics-tools",
              "date": "2026-05-08",
              "words": 580,
              "completeFrontmatter": true,
              "draft": false
            },
            {
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
        "expectedLiveCoverage": {
          "slug": "2026-05-20-ecommerce-conversion-analytics-tools",
          "title": "Ecommerce Conversion Analytics Tools for 2026",
          "blogUrl": "https://sellkit.neogenesis.app/blog",
          "detailUrl": "https://sellkit.neogenesis.app/blog/2026-05-20-ecommerce-conversion-analytics-tools",
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
    "gscOpportunityTotal": 112,
    "pipelinePassed": true,
    "liveCoverageMissingCount": 0,
    "liveCoverageMissing": [],
    "failingSites": []
  },
  "passed": true,
  "output": {
    "stampedJson": "data\\sbu-growth\\search-growth-flywheel-2026-05-20T15-51-09-09-00.json",
    "stampedMd": "data\\sbu-growth\\search-growth-flywheel-2026-05-20T15-51-09-09-00.md",
    "latestJson": "data\\sbu-growth\\search-growth-flywheel-latest.json",
    "latestMd": "data\\sbu-growth\\search-growth-flywheel-latest.md",
    "writesDefaultLatest": true,
    "written": [
      "data\\sbu-growth\\search-growth-flywheel-2026-05-20T15-51-09-09-00.json",
      "data\\sbu-growth\\search-growth-flywheel-2026-05-20T15-51-09-09-00.md",
      "data\\sbu-growth\\search-growth-flywheel-latest.json",
      "data\\sbu-growth\\search-growth-flywheel-latest.md"
    ]
  }
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
  "generatedAt": "2026-05-20T15:50:22+09:00",
  "passed": true,
  "criticalIssueCount": 0,
  "warningCount": 0,
  "issues": [],
  "warnings": []
}
```

### posthog-7d

```text
      "lastSeen": "2026-05-20T15:51:40.382000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    },
    {
      "site": "reviewlab",
      "events": 102,
      "pageviews": 64,
      "decisionEvents": 1,
      "actionEvents": 1,
      "legacyActionEvents": 38,
      "users": 58,
      "lastSeen": "2026-05-20T15:51:44.398000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    },
    {
      "site": "ur-wrong",
      "events": 96,
      "pageviews": 18,
      "decisionEvents": 0,
      "actionEvents": 0,
      "legacyActionEvents": 78,
      "users": 8,
      "lastSeen": "2026-05-20T15:51:51.370000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    },
    {
      "site": "kott",
      "events": 53,
      "pageviews": 22,
      "decisionEvents": 1,
      "actionEvents": 1,
      "legacyActionEvents": 31,
      "users": 22,
      "lastSeen": "2026-05-20T15:51:55.213000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    },
    {
      "site": "whylab",
      "events": 4,
      "pageviews": 4,
      "decisionEvents": 0,
      "actionEvents": 0,
      "legacyActionEvents": 0,
      "users": 4,
      "lastSeen": "2026-05-20T15:52:06.984000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    },
    {
      "site": "ethicaai",
      "events": 30,
      "pageviews": 9,
      "decisionEvents": 0,
      "actionEvents": 0,
      "legacyActionEvents": 21,
      "users": 9,
      "lastSeen": "2026-05-20T15:52:00.983000+09:00",
      "allowlistVersion": "2026-05-14.decision-events.v1"
    }
  ]
}
```

### ga4-report

```text
TOKEN OK (oauth_refresh_token)
NOTE: NeoGenesis subdomains are reported via shared property properties/526345390.

==========================================================================================
Site                     7d Users   7d Views  28d Users  28d Views    Today
==========================================================================================
NeoGenesis                     39         51        111        143        2
ToolPick                      367        387       1046       1165       41
UR WRONG                        2         11         25         65        0
K-OTT                           4          4         53         58        0
HeoYesol Portfolio             10         17         17         97        3
AIForge                         3          4          6          7        0
CraftDesk                      27         30         62         69        0
SellKit                         2          2          4          4        0
FinStack                        1          2          6          7        0
DeployStack                     4          5         13         14        0
ReviewLab                      27         37         33         43        3
WhyLab                          1          1          7          7        0
EthicaAI                        0          0          0          0        1
==========================================================================================
TOTAL                         487        551       1383       1679       50
==========================================================================================

Site                      Bounce%     AvgSec    Engage%    PV/Sess
------------------------------------------------------------------
ToolPick                    94.4%       7.2s       5.6%      1.03
UR WRONG                    75.0%      24.3s      25.0%      2.75
K-OTT                       71.4%      22.7s      28.6%      0.57
CraftDesk                   92.9%       3.3s       7.1%      1.07
DeployStack                 50.0%     292.8s      50.0%      1.25

Site                      This Wk    Last Wk      WoW %
--------------------------------------------------------
NeoGenesis                     39         18    +116.7%
ToolPick                      367        324     +13.3%
UR WRONG                        2          2      +0.0%
K-OTT                           4         13     -69.2%
HeoYesol Portfolio             10          3    +233.3%
AIForge                         3          0      NEW
CraftDesk                      27          0      NEW
SellKit                         2          0      NEW
FinStack                        1          0      NEW
DeployStack                     4          0      NEW
ReviewLab                      27          0      NEW
WhyLab                          1          0      NEW
==========================================================================================
```

