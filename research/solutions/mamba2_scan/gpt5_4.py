import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _chunk_local_kernel(
                X_ptr, A_ptr, B_ptr,
                Y0_ptr, P_ptr,
                Achunk_ptr, Schunk_ptr,
                L, D, C,
                stride_x_l, stride_x_d,
                stride_y_l, stride_y_d,
                stride_p_l, stride_p_d,
                stride_cs_l, stride_cs_d,
                BLOCK_T: tl.constexpr, BLOCK_D: tl.constexpr
            ):
                pid_c = tl.program_id(0)  # chunk id
                pid_d = tl.program_id(1)  # feature tile id

                d_off = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = d_off < D

                y = tl.zeros([BLOCK_D], dtype=tl.float32)
                p = tl.ones([BLOCK_D], dtype=tl.float32)

                base_t = pid_c * BLOCK_T

                for t in range(BLOCK_T):
                    idx_t = base_t + t
                    x = tl.load(X_ptr + idx_t * stride_x_l + d_off * stride_x_d, mask=mask_d, other=0.0)
                    a = tl.load(A_ptr + idx_t * stride_x_l + d_off * stride_x_d, mask=mask_d, other=0.0)
                    b = tl.load(B_ptr + idx_t * stride_x_l + d_off * stride_x_d, mask=mask_d, other=0.0)

                    x32 = x.to(tl.float32)
                    a32 = a.to(tl.float32)
                    b32 = b.to(tl.float32)

                    y = a32 * y + b32 * x32
                    p = p * a32

                    tl.store(Y0_ptr + idx_t * stride_y_l + d_off * stride_y_d, y.to(tl.float16), mask=mask_d)
                    tl.store(P_ptr + idx_t * stride_p_l + d_off * stride_p_d, p.to(tl.float16), mask=mask_d)

                # Store per-chunk accumulators
                tl.store(Achunk_ptr + pid_c * stride_cs_l + d_off * stride_cs_d, p.to(tl.float16), mask=mask_d)
                tl.store(Schunk_ptr + pid_c * stride_cs_l + d_off * stride_cs_d, y.to(tl.float16), mask=mask_d)

            @triton.jit
            def _scan_chunks_kernel(
                Achunk_ptr, Schunk_ptr, Ystart_ptr,
                num_chunks, D,
                stride_cs_l, stride_cs_d,
                stride_y_l, stride_y_d,
                BLOCK_D: tl.constexpr
            ):
                pid_d = tl.program_id(0)
                d_off = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = d_off < D

                y0 = tl.zeros([BLOCK_D], dtype=tl.float32)  # initial state is zero

                for c in range(0, num_chunks):
                    # Save starting state for chunk c
                    tl.store(Ystart_ptr + c * stride_y_l + d_off * stride_y_d, y0.to(tl.float16), mask=mask_d)
                    a = tl.load(Achunk_ptr + c * stride_cs_l + d_off * stride_cs_d, mask=mask_d, other=0.0).to(tl.float32)
                    s = tl.load(Schunk_ptr + c * stride_cs_l + d_off * stride_cs_d, mask=mask_d, other=0.0).to(tl.float32)
                    y0 = a * y0 + s

            @triton.jit
            def _apply_y0_kernel(
                Y0_ptr, P_ptr, Ystart_ptr, Yout_ptr,
                L, D, C,
                stride_y_l, stride_y_d,
                stride_p_l, stride_p_d,
                stride_ystart_l, stride_ystart_d,
                stride_out_l, stride_out_d,
                BLOCK_T: tl.constexpr, BLOCK_D: tl.constexpr
            ):
                pid_c = tl.program_id(0)  # chunk id
                pid_d = tl.program_id(1)  # feature tile

                d_off = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = d_off < D

                y_start = tl.load(Ystart_ptr + pid_c * stride_ystart_l + d_off * stride_ystart_d, mask=mask_d, other=0.0).to(tl.float32)

                base_t = pid_c * BLOCK_T
                for t in range(BLOCK_T):
                    idx_t = base_t + t
                    y0 = tl.load(Y0_ptr + idx_t * stride_y_l + d_off * stride_y_d, mask=mask_d, other=0.0).to(tl.float32)
                    p = tl.load(P_ptr + idx_t * stride_p_l + d_off * stride_p_d, mask=mask_d, other=0.0).to(tl.float32)
                    y = y0 + p * y_start
                    tl.store(Yout_ptr + idx_t * stride_out_l + d_off * stride_out_d, y.to(tl.float16), mask=mask_d)

            def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
                """
                Mamba2 chunked scan computation.

                Args:
                    X: Input tensor of shape (L, D) - input sequence (float16)
                    A: Input tensor of shape (L, D) - decay factors (float16)
                    B: Input tensor of shape (L, D) - input weights (float16)
                    chunk: Chunk size for parallel processing (default 128)
                    BD: Block dimension for feature dimension tiling (default 128)

                Returns:
                    Output tensor of shape (L, D) - scan output (float16)
                """
                assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be CUDA tensors"
                assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
                assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2, "Inputs must be 2D tensors"
                L, D = X.shape
                assert A.shape == (L, D) and B.shape == (L, D), "Input shapes must match"
                assert L % chunk == 0, "L must be divisible by chunk size"

                Xc = X.contiguous()
                Ac = A.contiguous()
                Bc = B.contiguous()

                n_chunks = L // chunk

                Y0 = torch.empty_like(Xc)  # y computed with y0=0 within chunk
                P = torch.empty_like(Xc)   # prefix products of a
                Achunk = torch.empty((n_chunks, D), device=Xc.device, dtype=torch.float16)
                Schunk = torch.empty((n_chunks, D), device=Xc.device, dtype=torch.float16)
                Ystart = torch.empty((n_chunks, D), device=Xc.device, dtype=torch.float16)
                Yout = torch.empty_like(Xc)

                grid1 = (n_chunks, triton.cdiv(D, BD))

                _chunk_local_kernel[grid1](
                    Xc, Ac, Bc,
                    Y0, P,
                    Achunk, Schunk,
                    L, D, chunk,
                    Xc.stride(0), Xc.stride(1),
                    Y0.stride(0), Y0.stride(1),
                    P.stride(0), P.stride(1),
                    Achunk.stride(0), Achunk.stride(1),
                    BLOCK_T=chunk, BLOCK_D=BD,
                    num_warps=4, num_stages=2
                )

                grid2 = (triton.cdiv(D, BD),)
                _scan_chunks_kernel[grid2](
                    Achunk, Schunk, Ystart,
                    n_chunks, D,
                    Achunk.stride(0), Achunk.stride(1),
                    Ystart.stride(0), Ystart.stride(1),
                    BLOCK_D=BD,
                    num_warps=4, num_stages=2
                )

                _apply_y0_kernel[grid1](
                    Y0, P, Ystart, Yout,
                    L, D, chunk,
                    Y0.stride(0), Y0.stride(1),
                    P.stride(0), P.stride(1),
                    Ystart.stride(0), Ystart.stride(1),
                    Yout.stride(0), Yout.stride(1),
                    BLOCK_T=chunk, BLOCK_D=BD,
                    num_warps=4, num_stages=2
                )

                return Yout
        """)
        return {"code": code}