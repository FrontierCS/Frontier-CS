# PCA kernel optimization — submission workflow

You are optimizing the `pcalib` package at `/app/pcalib`. Edit the package
(rewrite the internals of `pca`, add Triton kernel modules under `pcalib/`),
then submit a patch.

## Iterate locally

Run the public self-test to check correctness and get a rough speed signal on
the two public shapes (needs a GPU in the agent container):

```bash
bash /app/public_test.sh
```

## Submit

```bash
bash /app/make_submission.sh      # writes /app/solution.patch (pcalib diff)
bash /app/submit.sh               # enqueues it for the black-box judge
```

Submissions are asynchronous. Submit early and keep improving; use
`bash /app/submissions.sh` and `bash /app/wait_submission.sh <uuid>` to inspect
results.

## Rules

- Only files under `pcalib/` may change.
- Do not import external optimized libraries (write the kernels yourself), and
  do not access the environment, spawn processes, or use the network.
- Keep the public `pca(...)` signature and return contract unchanged.
- Subspace quality is gated (orthonormal components and captured variance vs the
  naive baseline); do not sacrifice correctness for speed beyond the allowed
  tolerance.
