# GSC Sitemap Submission — 2026-05-04

## Submission status
- API access: YES (service account `neogenesismaster@ethereal-cache-487709-s3.iam.gserviceaccount.com`)
- Submitted: YES
- API response: HTTP 204 No Content (PUT success)
- Verification token: `ToqjqeHF5YDoqmmQitcEtALmOkGezikhYnqP_-FLT2Q` (in `src/landing/src/app/layout.tsx`)
- Site URL (GSC property): `https://neogenesis.app/` (URL-prefix property, `siteOwner` permission)
- Feedpath: `https://neogenesis.app/sitemap.xml`
- Submission timestamp: `2026-05-04T05:42:20.210Z` (lastSubmitted, bumped from `2026-05-03T12:44:35.314Z`)
- isPending after PUT: `true` (Google scheduled re-crawl)

## Service account credentials
- Path: `C:\Users\yesol\Downloads\ethereal-cache-487709-s3-05b0a6adbe20.json`
- Project: `ethereal-cache-487709-s3`
- Type: `service_account`
- Scope used: `https://www.googleapis.com/auth/webmasters` (PUT/DELETE write access)
- Auth flow: JWT RS256 signed → OAuth 2.0 access token → Bearer header

## GSC sites accessible (13 total, all `siteOwner`)
- https://neogenesis.app/ ← submitted
- https://www.toolpick.dev/
- https://aiforge.neogenesis.app/
- https://craftdesk.neogenesis.app/
- https://deploystack.neogenesis.app/
- https://ethica.neogenesis.app/
- https://finstack.neogenesis.app/
- https://review.neogenesis.app/
- https://sellkit.neogenesis.app/
- https://whylab.neogenesis.app/
- https://heoyesol.kr/
- https://kott.kr/
- https://ur-wrong.com/

## Sitemap pre-submit verification
- HTTP status: 200
- XML well-formed: YES (valid `<?xml ... ?>` + `<urlset>` root)
- URL count (`<loc>` entries): **60**
- Broken URLs: 0 (sitemap fetched cleanly via Vercel)
- Sample URLs: `/`, `/about`, `/faq`, `/blog`, `/data`, `/data/research`, `/data/quant`, `/press`, `/awards`, `/wikipedia-drafts`, `/llms.txt`, `/llms-full.txt`, `/rss.xml`, blog posts, research articles, etc.

## GSC current state (per API response)
- `submitted`: 39 (Google's last-counted value, will refresh after re-crawl of 60-URL sitemap)
- `indexed`: 0 (pre-submission state — site is verified but Google hasn't started indexing)
- `errors`: 0
- `warnings`: 0

This explains why Google indexing has been slow: the sitemap was previously known but Google had not re-crawled it. The forced re-submission via PUT triggers a fresh crawl cycle.

## Bing Webmaster Tools (bonus)
- API access: NO (no Bing API key found in CREDENTIAL_BIBLE, `.env`, `.env.local`)
- Submitted: NO
- Note: Bing IndexNow has been failing with 403 (separate task). Bing Webmaster Tools API requires a separate API key from Bing Webmaster portal — not yet provisioned.

## Owner G2 actions remaining
- [ ] **Bing Webmaster Tools API key provisioning** — owner must visit https://www.bing.com/webmasters/, sign in with Microsoft account, add `neogenesis.app` as a property, complete verification (DNS or HTML file), then generate an API key under Settings → API access. Once obtained, store in `D:/00.test/neo-genesis/.env` as `BING_WEBMASTER_API_KEY` for sitemap submission via `https://ssl.bing.com/webmaster/api.svc/json/SubmitFeed`.
- [ ] **(Optional) Domain property migration** — current GSC property is URL-prefix (`https://neogenesis.app/`). Domain property (`neogenesis.app` covering all subdomains and protocols) would consolidate signals and is recommended long-term. Requires DNS TXT record verification.

## Reproducibility (script)

Path: ad-hoc Python — for re-submission, run:

```python
from urllib.parse import quote
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

SA_PATH = r"C:\Users\yesol\Downloads\ethereal-cache-487709-s3-05b0a6adbe20.json"
SCOPES = ["https://www.googleapis.com/auth/webmasters"]

creds = service_account.Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
creds.refresh(Request())
headers = {"Authorization": f"Bearer {creds.token}"}

site_enc = quote("https://neogenesis.app/", safe='')
feed_enc = quote("https://neogenesis.app/sitemap.xml", safe='')

url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_enc}/sitemaps/{feed_enc}"
r = requests.put(url, headers=headers, timeout=30)
print(r.status_code, r.text)  # expect 204 ''
```

## References
- Verification token location: `D:/00.test/neo-genesis/src/landing/src/app/layout.tsx` → `metadata.verification.google`
- GA4 service account JSON (same SA reused for GSC): `C:\Users\yesol\Downloads\ethereal-cache-487709-s3-05b0a6adbe20.json` — also referenced in `CREDENTIAL_BIBLE.md` line 221
- Google Search Console API docs: https://developers.google.com/webmaster-tools/v1/sitemaps
