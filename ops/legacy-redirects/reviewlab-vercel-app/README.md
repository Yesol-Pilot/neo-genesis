# ReviewLab legacy Vercel alias redirect

This tiny Vercel project exists only to make the stale Search Console property
`https://reviewlab.vercel.app/` non-404 and non-401.

All traffic is permanently redirected to the canonical ReviewLab domain:

```text
https://reviewlab.vercel.app/:path* -> https://review.neogenesis.app/:path*
```

The production ReviewLab app remains `src/sbu/reviewlab` and
`https://review.neogenesis.app/`.

