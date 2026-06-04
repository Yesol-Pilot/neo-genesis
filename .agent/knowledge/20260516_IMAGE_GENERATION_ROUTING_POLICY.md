# Image Generation Routing Policy

> Date: 2026-05-16
> Scope: Neo Genesis image generation only.
> Sources checked: Gamma Developer Docs, image model accepted values, API scope and limits.

## Decision

Use the Gamma API only for image-oriented generation where Gamma workspace/UI visibility is company-safe.
Do not use Gamma as the default deck, document, webpage, or broad social-content generator.

## Non-Negotiables

- Gamma API generations create Gamma artifacts and may appear in the Gamma workspace UI.
- If the owner asks for no Gamma UI exposure, route away from Gamma.
- If a Gamma history item would be embarrassing or inappropriate for company colleagues to see, route away from Gamma.
- Sensitive, private, legal, finance, credential, personal, adult, meme-prank, or unpublished strategy visuals must not use Gamma.
- Normal company-safe internal work images are allowed on Gamma.
- Local-first routes are preferred for privacy, iteration, and throwaway drafts.
- `local_comfyui` is on-demand only: agents start it hidden when needed, bind to localhost by default, and stop it after use when they started it.
- External image APIs remain G4/external-side-effect work unless a narrower standing approval exists for the specific pipeline.
- Never log raw prompts containing sensitive material, raw API keys, export URLs with secrets, or full request bodies.

## Provider Roles

| Provider | Use When | Avoid When |
| --- | --- | --- |
| `local_comfyui` | privacy, no UI history, iterative drafts, sensitive/personal work; on-demand local GPU work | hard deadline and local worker unavailable; resident always-on service mode |
| `codex_cli` | interactive or local agent-assisted image output, no Gamma workspace artifact | organization/model access is blocked |
| `gemini_api` | direct image API fallback, text-in-image or fast external generation | zero-retention is required but unavailable |
| `gamma_api` | public or company-safe internal image cards, social-card smoke tests, Gamma visual model comparison | no Gamma UI exposure, embarrassing prompts, sensitive prompts, deck/doc automation |

## Gamma Model Routing

Gamma supports many image models through `imageOptions.model` when `imageOptions.source` is `aiGenerated`.
Treat the list as time-sensitive and refresh from official docs before major routing changes.

Default Gamma routing:

- fast preview: `flux-kontext-fast` or `flux-2-klein`
- Korean/social card with text emphasis: `gemini-3-pro-image` when budget allows; `ideogram-v3-turbo` for lower-cost text-heavy output
- photorealistic/product-like output: `imagen-4-fast`, then `imagen-4-pro` for quality
- vector/brand-like output: `recraft-v4-svg` or `recraft-v3-svg`
- high-quality final: `gpt-image-1-high` or `recraft-v4-pro` only with explicit budget acceptance

## Routing Rule

1. If `company_safe == false`, route to local/non-Gamma.
2. If `sensitivity` is private/sensitive/legal/finance/credential/personal/adult, route to local/non-Gamma.
3. If `needs_gamma_ui_hidden == true`, route to local/non-Gamma.
4. If `allow_external_api == false`, route local.
5. If Gamma is allowed and the task is image/social-card only, select a Gamma image model by visual requirement and budget tier.
6. If Gamma is not allowed but external APIs are allowed, route to `codex_cli` or `gemini_api`.
7. Persist only artifact path, provider, model, and redacted audit metadata.

## Open Follow-Up

- Add a real `gamma_api` image-card adapter only after deciding whether API-created Gamma artifacts should be automatically archived or manually cleaned from the Gamma UI.
- Refresh model strings and credit costs before enabling scheduled or bulk runs.
