# Results

All numbers below are produced by `make eval`. Raw per-run files are in `results/raw/`.
Hardware: local WSL2 (dev), AWS t3.micro (test/deploy). See each row for the environment.

## Variants

| ID | Chunking | Search | Rerank | Embedding |
|----|----------|--------|--------|-----------|
| A  | Fixed 512-token | Vector only | No | all-MiniLM-L6-v2 |
| D  | Syntax-tree (AST) | Vector + identifier-FTS + symbol lookup, RRF | No | all-MiniLM-L6-v2 |
| F  | Same as D | Same | No | CodeRankEmbed (or Jina Code V2) |

## Splits

- **dev** — `psf/requests@3c7baaa`, `pallets/click@2247b35` (tuning allowed)
- **test** — `encode/httpx@b5addb6`, `pallets/flask@49943b5`, `scrapy/scrapy@943e31d` (run once, Week 3, never tuned against)

## Retrieval metrics

| Date       | Variant | Split | Hit@5 | Recall@10 | MRR | p50 (ms) | p95 (ms) | Index (MB) | Raw |
|------------|---------|-------|-------|-----------|-----|----------|----------|------------|-----|
| TBD        | A       | dev   | TBD   | TBD       | TBD | TBD      | TBD      | TBD        | TBD |
| TBD        | D       | dev   | TBD   | TBD       | TBD | TBD      | TBD      | TBD        | TBD |
| TBD        | F       | dev   | TBD   | TBD       | TBD | TBD      | TBD      | TBD        | TBD |
| TBD        | D       | test  | TBD   | TBD       | TBD | TBD      | TBD      | TBD        | TBD |

## End-to-end

| Date | Variant | Split | Correct | Partial | Wrong | Invalid-citation rate | False-answer rate (5 unanswerable) | Raw |
|------|---------|-------|---------|---------|-------|-----------------------|-------------------------------------|-----|
| TBD  | TBD     | TBD   | TBD     | TBD     | TBD   | TBD                   | TBD                                 | TBD |



| Date       | Variant | Split | Hit@5 | Recall@10 | MRR | p50 (ms) | p95 (ms) | Index (MB) | Raw |
|------------|---------|-------|-------|-----------|-----|----------|----------|------------|-----|
| 2026-11-24 | A       | dev   | 0.6167| 0.7250    | 0.4713| TBD    | TBD      | TBD        | (Variant A baseline) |
| 2026-11-24 | D       | dev   | 0.9833| 0.9667    | 0.9444| TBD    | TBD      | TBD        | results/raw/2026-11-24-variant-D-dev.csv |