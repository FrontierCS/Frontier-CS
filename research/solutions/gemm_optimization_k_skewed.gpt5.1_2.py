import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def gelu(x):
                return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


            def _get_configs():
                return [
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=3, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 16, 'GROUP_M': 8}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4}, num_stages=4, num_warps=8),
                ]


            def _make_matmul_kernel(dtype):
                configs = _get_configs()

                @triton.autotune(configs=configs, key=['M', 'N', 'K'])
                @triton.jit
                def kernel(
                    a_ptr: tl.pointer_type(dtype=dtype),
                    b_ptr: tl.pointer_type(dtype=dtype),
                    c_ptr: tl.pointer_type(dtype=dtype),
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                    BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr,
                ):
                    pid = tl.program_id(axis=0)
                    grid_n = tl.cdiv(N, BLOCK_N)
                    pid_m = pid // grid_n
                    pid_n = pid % grid_n

                    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                    offs_k = tl.arange(0, BLOCK_K)

                    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
                    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    k = 0
                    while k < K:
                        k_vec = k + offs_k
                        a_mask = (offs_m[:, None] < M) & (k_vec[None, :] < K)
                        b_mask = (k_vec[:, None] < K) & (offs_n[None, :] < N)

                        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

                        acc += tl.dot(a, b)

                        a_ptrs += BLOCK_K * stride_ak
                        b_ptrs += BLOCK_K * stride_bk
                        k += BLOCK_K

                    acc = gelu(acc)

                    c = acc.to(dtype)
                    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
                    tl.store(c_ptrs, c, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

                return kernel


            _matmul_kernels = {}


            def _get_kernel_for_dtype(torch_dtype):
                kernel = _matmul_kernels.get(torch_dtype, None)
                if kernel is not None:
                    return kernel
                if torch_dtype == torch.float16:
                    triton_dtype = tl.float16
                elif torch_dtype == torch.bfloat16:
                    triton_dtype = tl.bfloat16
                elif torch_dtype == torch.float32:
                    triton_dtype = tl.float32
                else:
                    raise TypeError(f"Unsupported dtype: {torch_dtype}")
                kernel = _make_matmul_kernel(triton_dtype)
                _matmul_kernels[torch_dtype] = kernel
                return kernel


            def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
                if a.dim() != 2 or b.dim() != 2:
                    raise ValueError("Input tensors must be 2D matrices")
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Inner dimensions must match for matmul")
                if a.device != b.device:
                    raise ValueError("Input tensors must be on the same device")
                if a.dtype != b.dtype:
                    raise ValueError("Input tensors must have the same dtype")

                if not a.is_cuda:
                    out = torch.matmul(a, b)
                    return torch.nn.functional.gelu(out)

                M, K = a.shape
                Kb, N = b.shape
                if Kb != K:
                    raise ValueError("Incompatible matrix shapes for multiplication")

                kernel = _get_kernel_for_dtype(a.dtype)

                c = torch.empty((M, N), device=a.device, dtype=a.dtype)

                stride_am, stride_ak = a.stride()
                stride_bk, stride_bn = b.stride()
                stride_cm, stride_cn = c.stride()

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
                )

                kernel[grid](
                    a, b, c,
                    M, N, K,
                    stride_am, stride_ak,
                    stride_bk, stride_bn,
                    stride_cm, stride_cn,
                )

                return c
            '''
        )
        return {"code": code}