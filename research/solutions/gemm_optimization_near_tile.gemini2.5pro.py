import torch
import triton
import triton.language as tl
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        
        # Use textwrap.dedent to remove leading whitespace from the code string.
        # This makes the code more readable and avoids indentation errors.
        code = textwrap.dedent("""
        import torch
        import triton
        import triton.language as tl

        @triton.jit
        def gelu(x):
            return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

        @triton.autotune(
            configs=[
                # Basic configurations covering different tile shapes and parameters
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'num_stages': 3, 'num_warps': 8}),
                triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'num_stages': 5, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'num_stages': 5, 'num_warps': 4}),
                
                # Configurations with larger BLOCK_K for more work per thread
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8, 'num_stages': 3, 'num_warps': 8}),
                triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'num_stages': 3, 'num_warps': 8}),
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8, 'num_stages': 4, 'num_warps': 4}),

                # Configurations with even larger BLOCK_K
                triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128, 'GROUP_M': 8, 'num_stages': 3, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128, 'GROUP_M': 8, 'num_stages': 3, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128, 'GROUP_M': 8, 'num_stages': 2, 'num_warps': 8}),

                # Configurations for smaller matrices (no grouping)
                triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 1, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_M': 1, 'num_stages': 4, 'num_warps': 4}),
                triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128, 'GROUP_M': 1, 'num_stages': 2, 'num_warps': 4}),
            ],
            key=['M', 'N', 'K', 'stride_am', 'stride_ak', 'stride_bk', 'stride_bn', 'stride_cm', 'stride_cn'],
        )
        @triton.jit
        def matmul_kernel(
            a_ptr, b_ptr, c_ptr,
            M, N, K,
            stride_am, stride_ak,
            stride_bk, stride_bn,
            stride_cm, stride_cn,
            BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            GROUP_M: tl.constexpr
        ):
            pid = tl.program_id(axis=0)
            num_pid_m = tl.cdiv(M, BLOCK_M)
            num_pid_n = tl.cdiv(N, BLOCK_N)
            
            # Grouping logic for better L2 cache performance
            num_pid_in_group = GROUP_M * num_pid_n
            group_id = pid // num_pid_in_group
            first_pid_m = group_id * GROUP_M
            group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
            pid_m = first_pid_m + (pid % group_size_m)
            pid_n = (pid % num_pid_in_group) // group_size_m

            # Create offsets for the M and N dimensions
            offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
            offs_k = tl.arange(0, BLOCK_K)
            
            # Create pointers to the first elements of the A and B tiles
            a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
            b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

            # Initialize accumulator with zeros in float32 for precision
            accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

            # Main loop over the K dimension
            for k in range(0, K, BLOCK_K):
                # Create masks for loading A and B tiles to handle boundary conditions
                k_offsets = k + offs_k
                a_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
                b_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)
                
                # Load A and B tiles from global memory
                a = tl.load(a_ptrs, mask=a_mask, other=0.0)
                b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                
                # Perform the matrix multiplication and accumulate the result
                accumulator += tl.dot(a, b, allow_tf32=True)
                
                # Advance pointers for the next iteration
                a_ptrs += BLOCK_K * stride_ak
                b_ptrs += BLOCK_K * stride_bk

            # Cast the accumulator to the output data type
            c_dtype = c_ptr.dtype.element_ty
            c_val = accumulator.to(c_dtype)
            
            # Apply GELU activation
            c_val = gelu(c_val)

            # Create pointers and mask for storing the C tile
            c_ptrs = c_ptr + stride_cm * offs_m[:, None] + stride_cn * offs_n[None, :]
            c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
            
            # Store the result back to global memory
            tl.store(c_ptrs, c_val, mask=c_mask)

        def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
            \"\"\"
            Matrix multiplication with GELU activation.
            
            Args:
                a: Input tensor of shape (M, K)
                b: Input tensor of shape (K, N)
            
            Returns:
                Output tensor of shape (M, N) with GELU activation applied
            \"\"\"
            # Input validation
            assert a.shape[1] == b.shape[0], "incompatible dimensions for matmul"
            assert len(a.shape) == 2 and len(b.shape) == 2, "inputs must be 2D tensors"

            M, K = a.shape
            _, N = b.shape

            # Allocate the output tensor
            c = torch.empty((M, N), device=a.device, dtype=a.dtype)

            # Early exit for empty matrices
            if M == 0 or N == 0:
                return c

            # Define the grid for kernel launch
            grid = lambda META: (
                triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
            )
            
            # Launch the Triton kernel
            matmul_kernel[grid](
                a, b, c,
                M, N, K,
                a.stride(0), a.stride(1),
                b.stride(0), b.stride(1),
                c.stride(0), c.stride(1)
            )

            return c
        """)
        return {"code": code}