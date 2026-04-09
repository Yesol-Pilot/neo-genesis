# 2026-04-08 GA4 Shared Property Learning

## Conclusion

- `AIForge`, `CraftDesk`, `DeployStack`, `FinStack`, `SellKit` are not reported from separate GA4 properties for operations.
- These SBU sites must be reported from the shared GA4 property `NeoGenesis - Production` (`properties/526345390`) using `hostName` filters.

## Shared Property SSOT

- Property: `NeoGenesis - Production`
- Property ID: `526345390`
- Web stream name: `NeoGenesis Web`
- Web stream ID: `13680678643`
- Measurement ID: `G-0GVNYZLEMX`
- Default URI: `https://neogenesis.app`

## Host Mapping

- `aiforge.neogenesis.app`
- `craftdesk.neogenesis.app`
- `deploystack.neogenesis.app`
- `finstack.neogenesis.app`
- `sellkit.neogenesis.app`
- Related shared hosts also present in the same property:
  - `review.neogenesis.app`
  - `whylab.neogenesis.app`
  - `ethica.neogenesis.app`

## What Was Verified

- `ToolPick` property (`properties/524659689`) does not contain the five NeoGenesis SBU hosts.
- Shared property `properties/526345390` contains the five SBU hosts with actual traffic.
- In GA4 Admin, the service account `neogenesismaster@ethereal-cache-487709-s3.iam.gserviceaccount.com` is already present as `관리자` on the shared property.
- `dpthf1537@gmail.com` is also `관리자` on the shared property.

## Operational Rule

- Treat `properties/526345390` + `hostName EXACT` as the reporting source of truth for the five NeoGenesis SBU sites.
- Do not assume that the live HTML `G-...` snippet shown on each site is the same thing as the canonical reporting source.
- For diagnostics and reporting scripts, prefer shared-property aggregation over per-site property guesses.

## Script Rule

- `scripts/ga4_traffic_report.py` should report the five SBU sites by querying `properties/526345390` with exact `hostName` filters.
- `scripts/ga4_check_streams.py` should record the shared property stream and annotate the affected SBU sites with `sharedProperty` and `host`.
