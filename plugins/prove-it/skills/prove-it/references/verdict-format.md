# Verdict format

Close every verification with exactly this block. Three lines, no preamble.

```
CLAIM    <one falsifiable sentence, naming the environment>
VERDICT  PROVEN | NOT PROVEN | UNPROVABLE HERE
PROOF    <artifact path> - <the single decisive line from it>
```

## Examples

```
CLAIM    https://example.com/pricing returns 200 and contains "Pro plan" on production.
VERDICT  PROVEN
PROOF    .prove-it/http-pricing-20260905T142211Z.json - status 200, cf-cache-status MISS, matched "Pro plan"
```

```
CLAIM    The Meta pixel fires a PageView on the production home page.
VERDICT  PROVEN
PROOF    .prove-it/page-home-20260905T142530Z.json - request https://www.facebook.com/tr/?id=...&ev=PageView -> 200
```

```
CLAIM    The migration added orders.refunded_at on the production database.
VERDICT  UNPROVABLE HERE
PROOF    none - no production credentials in this session. The migration file is written and reviewed; nothing was run.
```

```
CLAIM    The signup form no longer double-submits.
VERDICT  NOT PROVEN
PROOF    .prove-it/page-signup-20260905T143012Z.json - two POST /api/signup requests captured, 200 and 409
```

## Rules

- One claim per block. Two claims, two blocks.
- `PROOF` cites a file that exists. If you cannot cite one, the verdict is not PROVEN.
- Quote the decisive line verbatim. Do not summarise it into an adjective.
- A NOT PROVEN verdict goes at the top of your reply, not the bottom.
- Never write PROVEN for something you inferred. Inference goes in prose, outside the block.
