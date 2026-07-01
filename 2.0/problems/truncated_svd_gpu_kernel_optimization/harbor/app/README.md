# Truncated SVD kernel optimization — submission workflow

You are optimizing the `tsvdlib` package at `/app/tsvdlib`. Edit the package
(rewrite the internals of `truncated_svd`, add Triton kernel modules under
`tsvdlib/`), then submit a patch.

## Iterate locally

Run the public self-test to check correctness and get a rough speed signal on
the two public shapes (needs a GPU in the agent container):

```bash
bash /app/public_test.sh
```

## Submit

```bash
bash /app/make_submission.sh      # writes /app/solution.patch (tsvdlib diff)
bash /app/submit.sh               # enqueues it for the black-box judge
```

Submissions are asynchronous. Submit early and keep improving; use
`bash /app/submissions.sh` and `bash /app/wait_submission.sh <uuid>` to inspect
results.

## Rules

- Only files under `tsvdlib/` may change.
- Do not import external optimized libraries (write the kernels yourself), and
  do not access the environment, spawn processes, or use the network.
- Keep the public `truncated_svd(...)` signature and return contract unchanged.
- Low-rank factorization quality is gated (orthonormal components + captured
  energy vs the naive baseline); do not sacrifice correctness for speed beyond
  the allowed tolerance.
