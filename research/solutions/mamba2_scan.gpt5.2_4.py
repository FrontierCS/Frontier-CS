import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent(
            r"""
            import torch
            import triton
            import triton.language as tl

            _buf_cache = {}

            @triton.jit
            def _chunk_params_kernel(
                X_ptr, A_ptr, B_ptr,
                M_ptr, C_ptr,
                stride_x0: tl.constexpr, stride_x1: tl.constexpr,
                stride_a0: tl.constexpr, stride_a1: tl.constexpr,
                stride_b0: tl.constexpr, stride_b1: tl.constexpr,
                stride_mc0: tl.constexpr, stride_mc1: tl.constexpr,
                D: tl.constexpr,
                CHUNK: tl.constexpr,
                BD: tl.constexpr,
            ):
                pid_chunk = tl.program_id(0)
                pid_d = tl.program_id(1)

                d = pid_d * BD + tl.arange(0, BD)
                mask_d = d < D

                base_t = pid_chunk * CHUNK

                m = tl.full([BD], 1.0, tl.float32)
                c = tl.zeros([BD], tl.float32)

                for i in tl.static_range(0, CHUNK, 1, num_stages=2):
                    t = base_t + i
                    x = tl.load(X_ptr + t * stride_x0 + d * stride_x1, mask=mask_d, other=0.0).to(tl.float32)
                    a = tl.load(A_ptr + t * stride_a0 + d * stride_a1, mask=mask_d, other=1.0).to(tl.float32)
                    b = tl.load(B_ptr + t * stride_b0 + d * stride_b1, mask=mask_d, other=0.0).to(tl.float32)
                    u = b * x
                    c = a * c + u
                    m = a * m

                tl.store(M_ptr + pid_chunk * stride_mc0 + d * stride_mc1, m, mask=mask_d)
                tl.store(C_ptr + pid_chunk * stride_mc0 + d * stride_mc1, c, mask=mask_d)

            @triton.jit
            def _chunk_state_kernel(
                M_ptr, C_ptr,
                Y0_ptr,
                stride_mc0: tl.constexpr, stride_mc1: tl.constexpr,
                stride_y00: tl.constexpr, stride_y01: tl.constexpr,
                NCHUNKS: tl.constexpr,
                D: tl.constexpr,
                BD: tl.constexpr,
            ):
                pid_d = tl.program_id(0)
                d = pid_d * BD + tl.arange(0, BD)
                mask_d = d < D

                y = tl.zeros([BD], tl.float32)

                for j in tl.static_range(0, NCHUNKS, 1, num_stages=1):
                    tl.store(Y0_ptr + j * stride_y00 + d * stride_y01, y, mask=mask_d)
                    m = tl.load(M_ptr + j * stride_mc0 + d * stride_mc1, mask=mask_d, other=1.0).to(tl.float32)
                    c = tl.load(C_ptr + j * stride_mc0 + d * stride_mc1, mask=mask_d, other=0.0).to(tl.float32)
                    y = m * y + c

            @triton.jit
            def _chunk_output_kernel(
                X_ptr, A_ptr, B_ptr,
                Y0_ptr,
                Y_ptr,
                stride_x0: tl.constexpr, stride_x1: tl.constexpr,
                stride_a0: tl.constexpr, stride_a1: tl.constexpr,
                stride_b0: tl.constexpr, stride_b1: tl.constexpr,
                stride_y00: tl.constexpr, stride_y01: tl.constexpr,
                stride_y0: tl.constexpr, stride_y1: tl.constexpr,
                D: tl.constexpr,
                CHUNK: tl.constexpr,
                BD: tl.constexpr,
            ):
                pid_chunk = tl.program_id(0)
                pid_d = tl.program_id(1)

                d = pid_d * BD + tl.arange(0, BD)
                mask_d = d < D

                base_t = pid_chunk * CHUNK
                y = tl.load(Y0_ptr + pid_chunk * stride_y00 + d * stride_y01, mask=mask_d, other=0.0).to(tl.float32)

                for i in tl.static_range(0, CHUNK, 1, num_stages=2):
                    t = base_t + i
                    x = tl.load(X_ptr + t * stride_x0 + d * stride_x1, mask=mask_d, other=0.0).to(tl.float32)
                    a = tl.load(A_ptr + t * stride_a0 + d * stride_a1, mask=mask_d, other=1.0).to(tl.float32)
                    b = tl.load(B_ptr + t * stride_b0 + d * stride_b1, mask=mask_d, other=0.0).to(tl.float32)
                    y = a * y + b * x
                    tl.store(Y_ptr + t * stride_y0 + d * stride_y1, y.to(tl.float16), mask=mask_d)

            def _get_cached_buffers(device, nchunks, D, dtype_out=torch.float16):
                key = (device, nchunks, D, dtype_out)
                buf = _buf_cache.get(key, None)
                if buf is None:
                    M = torch.empty((nchunks, D), device=device, dtype=torch.float32)
                    C = torch.empty((nchunks, D), device=device, dtype=torch.float32)
                    Y0 = torch.empty((nchunks, D), device=device, dtype=torch.float32)
                    buf = (M, C, Y0)
                    _buf_cache[key] = buf
                return buf

            def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
                if not (X.is_cuda and A.is_cuda and B.is_cuda):
                    raise ValueError("X, A, B must be CUDA tensors")
                if not (X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16):
                    raise ValueError("X, A, B must be float16")
                if X.ndim != 2 or A.ndim != 2 or B.ndim != 2:
                    raise ValueError("X, A, B must be 2D tensors with shape (L, D)")
                if X.shape != A.shape or X.shape != B.shape:
                    raise ValueError("X, A, B must have the same shape (L, D)")

                L, D = X.shape
                if L % chunk != 0:
                    raise ValueError("L must be divisible by chunk")
                nchunks = L // chunk

                M, C, Y0 = _get_cached_buffers(X.device, nchunks, D)

                Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

                grid1 = (nchunks, triton.cdiv(D, BD))
                _chunk_params_kernel[grid1](
                    X, A, B,
                    M, C,
                    stride_x0=X.stride(0), stride_x1=X.stride(1),
                    stride_a0=A.stride(0), stride_a1=A.stride(1),
                    stride_b0=B.stride(0), stride_b1=B.stride(1),
                    stride_mc0=M.stride(0), stride_mc1=M.stride(1),
                    D=D,
                    CHUNK=chunk,
                    BD=BD,
                    num_warps=4,
                )

                grid2 = (triton.cdiv(D, BD),)
                _chunk_state_kernel[grid2](
                    M, C,
                    Y0,
                    stride_mc0=M.stride(0), stride_mc1=M.stride(1),
                    stride_y00=Y0.stride(0), stride_y01=Y0.stride(1),
                    NCHUNKS=nchunks,
                    D=D,
                    BD=BD,
                    num_warps=4,
                )

                grid3 = (nchunks, triton.cdiv(D, BD))
                _chunk_output_kernel[grid3](
                    X, A, B,
                    Y0,
                    Y,
                    stride_x0=X.stride(0), stride_x1=X.stride(1),
                    stride_a0=A.stride(0), stride_a1=A.stride(1),
                    stride_b0=B.stride(0), stride_b1=B.stride(1),
                    stride_y00=Y0.stride(0), stride_y01=Y0.stride(1),
                    stride_y0=Y.stride(0), stride_y1=Y.stride(1),
                    D=D,
                    CHUNK=chunk,
                    BD=BD,
                    num_warps=4,
                )

                return Y
            """
        ).strip()
        return {"code": kernel_code}