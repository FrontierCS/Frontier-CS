import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    assert W.shape[0] == K and B.shape[0] == N and targets.shape[0] == M
    device = X.device
    BLOCK_M = 64
    BLOCK_N = 256
    BLOCK_K = 128

    def cdiv(x, y):
        return (x + y - 1) // y

    grid_m = cdiv(M, BLOCK_M)
    grid_n = cdiv(N, BLOCK_N)

    row_max = torch.full((M,), float('-1e9'), dtype=torch.float32, device=device)
    row_max_ptr = row_max.data_ptr()
    row_max_stride = row_max.stride(0) * row_max.dtype.itemsize

    x_ptr = X.data_ptr()
    x_stride_m = X.stride(0) * X.dtype.itemsize
    x_stride_k = X.stride(1) * X.dtype.itemsize

    w_ptr = W.data_ptr()
    w_stride_k = W.stride(0) * W.dtype.itemsize
    w_stride_n = W.stride(1) * W.dtype.itemsize

    b_ptr = B.data_ptr()
    b_stride = B.stride(0) * B.dtype.itemsize

    @triton.jit
    def first_pass_kernel(
        row_max_ptr, row_max_stride,
        X_ptr, X_stride_m, X_stride_k,
        W_ptr, W_stride_k, W_stride_n,
        B_ptr, B_stride,
        M, N, K,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        m_start = pid_m * BLOCK_M
        n_start = pid_n * BLOCK_N
        m_end = tl.minimum(m_start + BLOCK_M, M)
        n_end = tl.minimum(n_start + BLOCK_N, N)
        offs_m = tl.arange(0, BLOCK_M) + m_start
        offs_n = tl.arange(0, BLOCK_N) + n_start
        offs_k = tl.arange(0, BLOCK_K)
        m_mask = offs_m < M
        n_mask = offs_n < N
        valid_n_mask = tl.arange(0, BLOCK_N) < (n_end - n_start)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            end_k = tl.minimum(start_k + BLOCK_K, K)
            lo_k = tl.arange(0, BLOCK_K)
            k_mask = lo_k < (end_k - start_k)
            x_offs_m = offs_m[:, None] * X_stride_m
            x_offs_k = (start_k + lo_k)[None, :] * X_stride_k
            x_offs = x_offs_m + x_offs_k
            x_mask = m_mask[:, None] & k_mask[None, :]
            x_ptrs = X_ptr + x_offs.flatten()
            x = tl.load(x_ptrs, mask=x_mask.flatten(), other=0.0, dtype=tl.float16)
            x = tl.reshape(x, (BLOCK_M, BLOCK_K)).to(tl.float32)
            w_offs_k = (start_k + lo_k)[:, None] * W_stride_k
            w_offs_n = offs_n[None, :] * W_stride_n
            w_offs = w_offs_k + w_offs_n
            w_mask = k_mask[:, None] & n_mask[None, :]
            w_ptrs = W_ptr + w_offs.flatten()
            w = tl.load(w_ptrs, mask=w_mask.flatten(), other=0.0, dtype=tl.float16)
            w = tl.reshape(w, (BLOCK_K, BLOCK_N)).to(tl.float32)
            acc += tl.dot(x, w)
        b_offs = offs_n * B_stride
        b_mask = n_mask
        b_ptrs = B_ptr + b_offs
        b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float32)
        b_bc = tl.broadcast_to(b[None, :], (BLOCK_M, BLOCK_N))
        logits = acc + b_bc
        for r in range(0, BLOCK_M):
            m_idx = m_start + r
            if m_idx >= M:
                continue
            masked = tl.where(valid_n_mask, logits[r], tl.float32(-1e9))
            lmax = tl.max(masked)
            tl.atomic_max(row_max_ptr + m_idx * row_max_stride, lmax)

    first_pass_kernel[(grid_m, grid_n)](
        row_max_ptr, row_max_stride,
        x_ptr, x_stride_m, x_stride_k,
        w_ptr, w_stride_k, w_stride_n,
        b_ptr, b_stride,
        M, N, K,
        BLOCK_M, BLOCK_N, BLOCK_K
    )

    sum_exp = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_exp_ptr = sum_exp.data_ptr()
    sum_exp_stride = sum_exp.stride(0) * sum_exp.dtype.itemsize

    target_exp = torch.zeros((M,), dtype=torch.float32, device=device)
    target_exp_ptr = target_exp.data_ptr()
    target_exp_stride = target_exp.stride(0) * target_exp.dtype.itemsize

    t_ptr = targets.data_ptr()
    t_stride = targets.stride(0) * targets.dtype.itemsize

    @triton.jit
    def second_pass_kernel(
        sum_exp_ptr, sum_exp_stride,
        target_exp_ptr, target_exp_stride,
        row_max_ptr, row_max_stride,
        targets_ptr, targets_stride,
        X_ptr, X_stride_m, X_stride_k,
        W_ptr, W_stride_k, W_stride_n,
        B_ptr, B_stride,
        M, N, K,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        m_start = pid_m * BLOCK_M
        n_start = pid_n * BLOCK_N
        m_end = tl.minimum(m_start + BLOCK_M, M)
        n_end = tl.minimum(n_start + BLOCK_N, N)
        offs_m = tl.arange(0, BLOCK_M) + m_start
        offs_n = tl.arange(0, BLOCK_N) + n_start
        offs_k = tl.arange(0, BLOCK_K)
        m_mask = offs_m < M
        n_mask = offs_n < N
        valid_n_mask = tl.arange(0, BLOCK_N) < (n_end - n_start)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            end_k = tl.minimum(start_k + BLOCK_K, K)
            lo_k = tl.arange(0, BLOCK_K)
            k_mask = lo_k < (end_k - start_k)
            x_offs_m = offs_m[:, None] * X_stride_m
            x_offs_k = (start_k + lo_k)[None, :] * X_stride_k
            x_offs = x_offs_m + x_offs_k
            x_mask = m_mask[:, None] & k_mask[None, :]
            x_ptrs = X_ptr + x_offs.flatten()
            x = tl.load(x_ptrs, mask=x_mask.flatten(), other=0.0, dtype=tl.float16)
            x = tl.reshape(x, (BLOCK_M, BLOCK_K)).to(tl.float32)
            w_offs_k = (start_k + lo_k)[:, None] * W_stride_k
            w_offs_n = offs_n[None, :] * W_stride_n
            w_offs = w_offs_k + w_offs_n
            w_mask = k_mask[:, None] & n_mask[None, :]
            w_ptrs = W_ptr + w_offs.flatten()
            w = tl.load(w_ptrs, mask=w_mask.flatten(), other=0.0, dtype=tl.float16)
            w = tl.reshape(w, (BLOCK_K, BLOCK_N)).to(tl.float32)
            acc += tl.dot(x, w)
        b_offs = offs_n * B_stride
        b_mask = n_mask
        b_ptrs = B_ptr + b_offs
        b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float32)
        b_bc = tl.broadcast_to(b[None, :], (BLOCK_M, BLOCK_N))
        logits = acc + b_bc
        rm_offs = offs_m * row_max_stride
        row_max_block = tl.load(row_max_ptr + rm_offs, mask=m_mask, other=float('-1e9'))
        row_max_bc = tl.broadcast_to(row_max_block[:, None], (BLOCK_M, BLOCK_N))
        shifted = logits - row_max_bc
        exp_shifted = tl.exp(shifted)
        exp_valid = tl.where(valid_n_mask[None, :], exp_shifted, 0.0)
        partial_sums = tl.sum(exp_valid, axis=1)
        for r in range(0, BLOCK_M):
            m_idx = m_start + r
            if m_idx >= M:
                continue
            tl.atomic_add(sum_exp_ptr + m_idx * sum_exp_stride, partial_sums[r])
        t_offs = offs_m * targets_stride
        targets_block = tl.load(targets_ptr + t_offs, mask=m_mask, other=-1, dtype=tl.int64)
        for r in range(0, BLOCK_M):
            m_idx = m_start + r
            if m_idx >= M:
                continue
            target = targets_block[r]
            j_local = tl.sub(target, tl.int64(n_start))
            contrib = 0.0
            for jj in range(0, BLOCK_N):
                if jj >= n_end - n_start:
                    break
                is_match = tl.equal(j_local, tl.int64(jj))
                this_c = tl.where(is_match, exp_valid[r, jj], 0.0)
                contrib += this_c
            tl.atomic_add(target_exp_ptr + m_idx * target_exp_stride, contrib)

    second_pass_kernel[(grid_m, grid_n)](
        sum_exp_ptr, sum_exp_stride,
        target_exp_ptr, target_exp_stride,
        row_max_ptr, row_max_stride,
        t_ptr, t_stride,
        x_ptr, x_stride_m, x_stride_k,
        w_ptr, w_stride_k, w_stride_n,
        b_ptr, b_stride,
        M, N, K,
        BLOCK_M, BLOCK_N, BLOCK_K
    )

    loss = -torch.log(target_exp / (sum_exp + 1e-8))
    return loss
'''
        return {"code": code}
