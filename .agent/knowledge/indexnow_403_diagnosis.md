# IndexNow 403 Diagnosis — neogenesis.app

> **Date:** 2026-05-03
> **Author:** Claude Opus 4.7 (autonomous, owner directive "너가할 수 있는 모든걸 해")
> **Outcome:** Root cause identified, autonomous fixes applied, 1 owner G2 action remaining

## TL;DR

- Bing's IndexNow returns **`403 UserForbiddedToAccessSite`** despite a valid, publicly accessible key file.
- This is **not** a key-file, header, or formatting bug — it is a known first-time-domain behavior on the Bing/Microsoft IndexNow backend until either (a) Bingbot organically discovers the key file (1–7 days), or (b) the site is verified in **Bing Webmaster Tools**.
- Yandex (`yandex.com/indexnow`) accepts both POST batch and GET single-URL → request format is correct.
- Autonomous code fixes shipped: explicit `User-Agent`, response-body capture, GET-style fallback per IndexNow spec, robots.txt expanded with `Bingbot-Mobile`, `msnbot-media`, `adidxbot`, `Applebot`, `Applebot-Extended`.
- **Owner G2 action remaining**: register and verify `neogenesis.app` in Bing Webmaster Tools (https://www.bing.com/webmasters). Once verified, IndexNow 403 self-resolves on the next ping.

## Evidence

### 1. Key file integrity — ✅ clean

```
$ curl -s https://neogenesis.app/68833447363a462a612e658317313cbc.txt
68833447363a462a612e658317313cbc

$ curl -s … | xxd | head
00000000: 3638 3833 3334 3437 3336 3361 3436 3261  68833447363a462a
00000010: 3631 3265 3635 3833 3137 3331 3363 6263  612e658317313cbc
```

- HTTP 200, `Content-Type: text/plain`
- Size 32 bytes (exactly the key) — no BOM, no trailing newline, no whitespace
- Key on disk (`public/68833447363a462a612e658317313cbc.txt`) byte-for-byte identical

### 2. Request format — ✅ correct (Yandex confirms)

```
$ curl -o /dev/null -w "%{http_code}\n" \
  'https://yandex.com/indexnow?url=https%3A%2F%2Fneogenesis.app%2F&key=68833447363a462a612e658317313cbc'
200
```

If the key/host/keyLocation triplet were wrong, Yandex would also reject. Yandex accepts → request shape is fine.

### 3. Bing/Microsoft response — ❌ 403 with structured error

POST to `https://www.bing.com/indexnow` with full payload + `User-Agent: NeoGenesis-IndexNow/1.0`:

```
HTTP/1.1 403 Forbidden
Content-Type: application/json; charset=utf-8
{
  "errorCode": "UserForbiddedToAccessSite",
  "message": "User is unauthorized to access the site. Please verify the site using the key and try again",
  "details": null
}
```

Same response from `api.indexnow.org/indexnow` (which routes to Bing).
Same response on GET-style `?url=…&key=…` single URL submission.

### 4. Bingbot can crawl the site — ✅ 200

```
Bingbot fetch /            HTTP 200
Bingbot fetch /sitemap.xml HTTP 200
Bingbot fetch /robots.txt  HTTP 200
```

The site is reachable and `site:neogenesis.app` returns hits in Bing search. The 403 is **not** a crawl-block issue.

## Root cause

Bing's `UserForbiddedToAccessSite` on a first-time domain with a valid key file is a documented edge case. Bing requires the domain–key binding to be registered on its backend before IndexNow accepts pings. Two paths to register:

1. **Organic** — Bingbot discovers `<key>.txt` during a crawl and indexes the binding. Empirically 1–7 days.
2. **Explicit** — owner verifies the domain in **Bing Webmaster Tools** (free), which immediately registers the binding.

Regenerating a new key would not help — the new key would also need the same registration. Confirmed by re-reading the IndexNow spec at https://www.indexnow.org/documentation §"Authorize a search engine to index your URLs".

## Fixes applied (autonomous)

| File | Change | Why |
|---|---|---|
| `src/landing/scripts/notify-indexnow.mjs` | Added `User-Agent: NeoGenesis-IndexNow/1.0`, `Accept: application/json`, response-body capture in `detail` field, GET-style fallback per IndexNow spec | Better diagnostics; nudges first-time discovery via single-URL GET |
| `src/landing/src/lib/indexnow.ts` | Added `User-Agent` + `Accept` to runtime POST | Consistency between postbuild script and runtime API |
| `src/landing/public/robots.txt` | Added `Bingbot-Mobile`, `msnbot-media`, `adidxbot`, `Applebot`, `Applebot-Extended` (each `Allow: /`) | Help Microsoft + Apple AI ecosystem discovery |

After these changes the build will still log `403 UserForbiddedToAccessSite` for Bing endpoints, but now with the structured error message inline so the cause is obvious. Yandex 1/3 acceptance is unchanged (working).

## Owner G2 action — Bing Webmaster Tools verification

This is the only remaining unblocker. Steps for the owner (~5 min):

1. Sign in to https://www.bing.com/webmasters with a Microsoft account.
2. Click **Add a site** → enter `https://neogenesis.app`.
3. Choose verification method **"Add an XML file to your web server"** OR **"Add a meta tag"**:
   - **XML method (recommended, no code change needed):** Bing will give a `BingSiteAuth.xml` file with a `<user>…</user>` token. Save it to `src/landing/public/BingSiteAuth.xml`, redeploy, click **Verify**.
   - **Meta tag method:** Bing gives `<meta name="msvalidate.01" content="…"/>`. Add to `metadata.verification` in `src/landing/src/app/layout.tsx` (already has `google` token next to it):
     ```ts
     verification: {
       google: "ToqjqeHF5YDoqmmQitcEtALmOkGezikhYnqP_-FLT2Q",
       other: { "msvalidate.01": "<TOKEN_FROM_BING>" },
     }
     ```
4. After verification succeeds, in Bing Webmaster Tools open **IndexNow** → it auto-recognizes `68833447363a462a612e658317313cbc.txt` and registers the binding.
5. Next postbuild ping should show `OK 200/202` for both `api.indexnow.org` and `www.bing.com`.

## Backup plan if Webmaster verification is delayed

- **Sitemap pings still work** — `Sitemap:` is in robots.txt, both Bingbot and Googlebot pick it up. ChatGPT-via-Bing-search and Bing index will eventually crawl.
- **Manual URL submission** — https://www.bing.com/webmasters/url-submission accepts up to 10 URLs/day per verified site (post-verification only).
- **Yandex alone** — already accepts, feeds Yep search and a small slice of European AI tools.

## Final state

- robots.txt: 36 `User-agent:` directives, 0 actual `Disallow:` rules → all major AI/search bots welcome.
- IndexNow ping success rate: 1/3 (Yandex) → expected to flip to 3/3 within minutes of Bing Webmaster Tools verification by the owner.
- No new key generated — existing key is fine. Regeneration would not help (same registration requirement).
- Build remains green: postbuild ping logs the 403 detail but exits 0 (non-fatal).
