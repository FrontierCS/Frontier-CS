import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _kernel_collect_prod_u(
                X_ptr, A_ptr, B_ptr,
                P_ptr, U_ptr,
                L, D,
                stride_x_l, stride_x_d,
                stride_a_l, stride_a_d,
                stride_b_l, stride_b_d,
                stride_p_c, stride_p_d,
                stride_u_c, stride_u_d,
                CHUNK: tl.constexpr,
                BLOCK_D: tl.constexpr,
            ):
                pid_c = tl.program_id(0)
                pid_d = tl.program_id(1)

                offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = offs_d < D

                base_l = pid_c * CHUNK

                # Initialize running values
                y = tl.zeros([BLOCK_D], dtype=tl.float32)
                p = tl.ones([BLOCK_D], dtype=tl.float32)

                # Base pointers for this chunk
                x_base = X_ptr + base_l * stride_x_l + offs_d * stride_x_d
                a_base = A_ptr + base_l * stride_a_l + offs_d * stride_a_d
                b_base = B_ptr + base_l * stride_b_l + offs_d * stride_b_d

                for t in range(CHUNK):
                    a_t = tl.load(a_base + t * stride_a_l, mask=mask_d, other=1.0).to(tl.float32)
                    b_t = tl.load(b_base + t * stride_b_l, mask=mask_d, other=0.0).to(tl.float32)
                    x_t = tl.load(x_base + t * stride_x_l, mask=mask_d, other=0.0).to(tl.float32)
                    y = a_t * y + b_t * x_t
                    p = p * a_t

                # Store per-chunk product and end-state (U accum)
                tl.store(P_ptr + pid_c * stride_p_c + offs_d * stride_p_d, p, mask=mask_d)
                tl.store(U_ptr + pid_c * stride_u_c + offs_d * stride_u_d, y, mask=mask_d)


            @triton.jit
            def _kernel_prefix_states(
                P_ptr, U_ptr, S_ptr,
                D,
                stride_p_c, stride_p_d,
                stride_u_c, stride_u_d,
                stride_s_c, stride_s_d,
                N_CHUNK: tl.constexpr,
                BLOCK_D: tl.constexpr,
            ):
                pid_d = tl.program_id(0)
                offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = offs_d < D

                s = tl.zeros([BLOCK_D], dtype=tl.float32)

                for i in range(N_CHUNK):
                    # Store state at the start of chunk i
                    tl.store(S_ptr + i * stride_s_c + offs_d * stride_s_d, s, mask=mask_d)
                    p = tl.load(P_ptr + i * stride_p_c + offs_d * stride_p_d, mask=mask_d, other=1.0).to(tl.float32)
                    u = tl.load(U_ptr + i * stride_u_c + offs_d * stride_u_d, mask=mask_d, other=0.0).to(tl.float32)
                    s = p * s + u


            @triton.jit
            def _kernel_write_outputs(
                X_ptr, A_ptr, B_ptr, S_ptr, Y_ptr,
                L, D,
                stride_x_l, stride_x_d,
                stride_a_l, stride_a_d,
                stride_b_l, stride_b_d,
                stride_s_c, stride_s_d,
                stride_y_l, stride_y_d,
                CHUNK: tl.constexpr,
                BLOCK_D: tl.constexpr,
            ):
                pid_c = tl.program_id(0)
                pid_d = tl.program_id(1)

                offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
                mask_d = offs_d < D

                base_l = pid_c * CHUNK

                # Load initial state for this chunk and D tile
                y = tl.load(S_ptr + pid_c * stride_s_c + offs_d * stride_s_d, mask=mask_d, other=0.0).to(tl.float32)

                # Base pointers for this chunk
                x_base = X_ptr + base_l * stride_x_l + offs_d * stride_x_d
                a_base = A_ptr + base_l * stride_a_l + offs_d * stride_a_d
                b_base = B_ptr + base_l * stride_b_l + offs_d * stride_b_d
                y_base = Y_ptr + base_l * stride_y_l + offs_d * stride_y_d

                for t in range(CHUNK):
                    a_t = tl.load(a_base + t * stride_a_l, mask=mask_d, other=1.0).to(tl.float32)
                    b_t = tl.load(b_base + t * stride_b_l, mask=mask_d, other=0.0).to(tl.float32)
                    x_t = tl.load(x_base + t * stride_x_l, mask=mask_d, other=0.0).to(tl.float32)
                    y = a_t * y + b_t * x_t
                    tl.store(y_base + t * stride_y_l, y.to(tl.float16), mask=mask_d)


            def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
                """
                Mamba2 chunked scan computation.
                y_t = a_t * y_{t-1} + b_t * x_t

                Args:
                    X: (L, D) float16 CUDA tensor
                    A: (L, D) float16 CUDA tensor
                    B: (L, D) float16 CUDA tensor
                    chunk: chunk length along sequence dimension (L must be divisible by chunk)
                    BD: tile size along feature dimension

                Returns:
                    Y: (L, D) float16 CUDA tensor
                """
                assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be CUDA tensors"
                assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
                assert X.shape == A.shape == B.shape and X.dim() == 2, "Shapes must match and be (L, D)"
                L, D = X.shape
                assert L % chunk == 0, "L must be divisible by chunk"

                device = X.device
                n_chunks = L // chunk

                # Allocate temporaries in fp32 for numerical stability
                P = torch.empty((n_chunks, D), dtype=torch.float32, device=device)  # product of a within chunk
                U = torch.empty((n_chunks, D), dtype=torch.float32, device=device)  # end state with zero init
                S = torch.empty((n_chunks, D), dtype=torch.float32, device=device)  # initial state per chunk

                Y = torch.empty_like(X, dtype=torch.float16, device=device)

                # Strides (in elements)
                stride_x_l, stride_x_d = X.stride()
                stride_a_l, stride_a_d = A.stride()
                stride_b_l, stride_b_d = B.stride()
                stride_p_c, stride_p_d = P.stride()
                stride_u_c, stride_u_d = U.stride()
                stride_s_c, stride_s_d = S.stride()
                stride_y_l, stride_y_d = Y.stride()

                grid_collect = (n_chunks, triton.cdiv(D, BD))
                _kernel_collect_prod_u[grid_collect](
                    X, A, B, P, U,
                    L, D,
                    stride_x_l, stride_x_d,
                    stride_a_l, stride_a_d,
                    stride_b_l, stride_b_d,
                    stride_p_c, stride_p_d,
                    stride_u_c, stride_u_d,
                    CHUNK=chunk,
                    BLOCK_D=BD,
                    num_warps=4,
                    num_stages=2,
                )

                grid_prefix = (triton.cdiv(D, BD),)
                _kernel_prefix_states[grid_prefix](
                    P, U, S,
                    D,
                    stride_p_c, stride_p_d,
                    stride_u_c, stride_u_d,
                    stride_s_c, stride_s_d,
                    N_CHUNK=n_chunks,
                    BLOCK_D=BD,
                    num_warps=4,
                    num_stages=2,
                )

                grid_write = (n_chunks, triton.cdiv(D, BD))
                _kernel_write_outputs[grid_write](
                    X, A, B, S, Y,
                    L, D,
                    stride_x_l, stride_x_d,
                    stride_a_l, stride_a_d,
                    stride_b_l, stride_b_d,
                    stride_s_c, stride_s_d,
                    stride_y_l, stride_y_d,
                    CHUNK=chunk,
                    BLOCK_D=BD,
                    num_warps=4,
                    num_stages=2,
                )

                return Y
        """)
        return {"code": code}