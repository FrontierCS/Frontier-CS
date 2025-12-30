import torch
import triton
import triton.language as tl
from typing import Tuple

@triton.jit
def _chunk_scan_forward_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
    STORE_STATE: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    
    state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L):
        if start_time + i < L and (start_time + i) % chunk_size == 0 and start_time + i > 0:
            state_ptr = State_ptr + ((start_time + i) // chunk_size - 1) * D + feature_offsets
            prev_state = tl.load(state_ptr, mask=mask_feature, other=0.0)
            state = prev_state
        
        state = state * a[:, i] + b[:, i] * x[:, i]
        y[:, i] = state
        
        if STORE_STATE and (i == BLOCK_L - 1 or start_time + i == L - 1):
            next_chunk_idx = (start_time + i + 1) // chunk_size
            if next_chunk_idx < num_chunks:
                state_ptr = State_ptr + next_chunk_idx * D + feature_offsets
                tl.store(state_ptr, state, mask=mask_feature)
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

@triton.jit
def _chunk_scan_backward_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    chunk_idx = (num_chunks - 1) - (pid // (D // BD))
    feature_block = pid % (D // BD)
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    
    next_state_ptr = State_ptr + (chunk_idx + 1) * D + feature_offsets
    if chunk_idx < num_chunks - 1:
        next_state = tl.load(next_state_ptr, mask=mask_feature, other=0.0)
    else:
        next_state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L - 1, -1, -1):
        if start_time + i < L:
            if i == BLOCK_L - 1 and chunk_idx < num_chunks - 1:
                state = next_state
            elif i < BLOCK_L - 1:
                state = y[:, i + 1]
            else:
                state = tl.zeros((BLOCK_D,), dtype=tl.float32)
            
            local_idx = (start_time + i) % chunk_size
            if local_idx == chunk_size - 1 and chunk_idx < num_chunks - 1:
                state = next_state
            
            state = state * a[:, i] + b[:, i] * x[:, i]
            y[:, i] = state
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

@triton.jit
def _chunk_scan_fused_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    
    if chunk_idx >= num_chunks:
        return
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    
    state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L):
        if start_time + i < L:
            if (start_time + i) % chunk_size == 0 and start_time + i > 0:
                prev_chunk_end = start_time + i - 1
                prev_chunk_idx = prev_chunk_end // chunk_size
                prev_time_in_chunk = chunk_size - 1
                
                prev_feature_offsets = start_feature + tl.arange(0, BLOCK_D)
                prev_mask = prev_feature_offsets < D
                
                prev_Y_ptr = Y_ptr + (prev_chunk_idx * chunk_size + prev_time_in_chunk) * chunk_stride + prev_feature_offsets * feature_stride
                prev_state = tl.load(prev_Y_ptr, mask=prev_mask, other=0.0)
                state = prev_state.to(tl.float32)
            
            state = state * a[:, i] + b[:, i] * x[:, i]
            y[:, i] = state
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

def chunk_scan(
    X: torch.Tensor,
    A: torch.Tensor, 
    B: torch.Tensor,
    chunk: int = 128,
    BD: int = 128
) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    
    device = X.device
    Y = torch.empty_like(X)
    
    num_chunks = L // chunk
    BLOCK_D = min(BD, triton.next_power_of_2(D))
    BLOCK_L = min(chunk, 128)
    
    if chunk <= 128 and D <= 512:
        grid = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_fused_kernel[grid](
            X, A, B, Y,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
        )
    else:
        State = torch.zeros((num_chunks + 1, D), dtype=torch.float32, device=device)
        
        grid_forward = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_forward_kernel[grid_forward](
            X, A, B, Y, State,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
            STORE_STATE=True,
        )
        
        grid_backward = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_backward_kernel[grid_backward](
            X, A, B, Y, State,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
        )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
from typing import Tuple

@triton.jit
def _chunk_scan_forward_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
    STORE_STATE: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    
    state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L):
        if start_time + i < L and (start_time + i) % chunk_size == 0 and start_time + i > 0:
            state_ptr = State_ptr + ((start_time + i) // chunk_size - 1) * D + feature_offsets
            prev_state = tl.load(state_ptr, mask=mask_feature, other=0.0)
            state = prev_state
        
        state = state * a[:, i] + b[:, i] * x[:, i]
        y[:, i] = state
        
        if STORE_STATE and (i == BLOCK_L - 1 or start_time + i == L - 1):
            next_chunk_idx = (start_time + i + 1) // chunk_size
            if next_chunk_idx < num_chunks:
                state_ptr = State_ptr + next_chunk_idx * D + feature_offsets
                tl.store(state_ptr, state, mask=mask_feature)
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

@triton.jit
def _chunk_scan_backward_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    chunk_idx = (num_chunks - 1) - (pid // (D // BD))
    feature_block = pid % (D // BD)
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    
    next_state_ptr = State_ptr + (chunk_idx + 1) * D + feature_offsets
    if chunk_idx < num_chunks - 1:
        next_state = tl.load(next_state_ptr, mask=mask_feature, other=0.0)
    else:
        next_state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L - 1, -1, -1):
        if start_time + i < L:
            if i == BLOCK_L - 1 and chunk_idx < num_chunks - 1:
                state = next_state
            elif i < BLOCK_L - 1:
                state = y[:, i + 1]
            else:
                state = tl.zeros((BLOCK_D,), dtype=tl.float32)
            
            local_idx = (start_time + i) % chunk_size
            if local_idx == chunk_size - 1 and chunk_idx < num_chunks - 1:
                state = next_state
            
            state = state * a[:, i] + b[:, i] * x[:, i]
            y[:, i] = state
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

@triton.jit
def _chunk_scan_fused_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    chunk_stride, feature_stride,
    L, D,
    chunk_size: tl.constexpr, BD: tl.constexpr,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk_size)
    
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    
    if chunk_idx >= num_chunks:
        return
    
    start_feature = feature_block * BD
    start_time = chunk_idx * chunk_size
    
    feature_offsets = start_feature + tl.arange(0, BLOCK_D)
    time_offsets = start_time + tl.arange(0, BLOCK_L)
    
    mask_feature = feature_offsets < D
    mask_time = time_offsets < L
    chunk_mask = time_offsets < min(L, start_time + chunk_size)
    final_mask = mask_time & mask_feature[:, None] & chunk_mask
    
    X_ptrs = X_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    A_ptrs = A_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    B_ptrs = B_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    Y_ptrs = Y_ptr + time_offsets[None, :] * chunk_stride + feature_offsets[:, None] * feature_stride
    
    x = tl.load(X_ptrs, mask=final_mask, other=0.0)
    a = tl.load(A_ptrs, mask=final_mask, other=0.0)
    b = tl.load(B_ptrs, mask=final_mask, other=0.0)
    
    state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    y = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float32)
    
    for i in range(BLOCK_L):
        if start_time + i < L:
            if (start_time + i) % chunk_size == 0 and start_time + i > 0:
                prev_chunk_end = start_time + i - 1
                prev_chunk_idx = prev_chunk_end // chunk_size
                prev_time_in_chunk = chunk_size - 1
                
                prev_feature_offsets = start_feature + tl.arange(0, BLOCK_D)
                prev_mask = prev_feature_offsets < D
                
                prev_Y_ptr = Y_ptr + (prev_chunk_idx * chunk_size + prev_time_in_chunk) * chunk_stride + prev_feature_offsets * feature_stride
                prev_state = tl.load(prev_Y_ptr, mask=prev_mask, other=0.0)
                state = prev_state.to(tl.float32)
            
            state = state * a[:, i] + b[:, i] * x[:, i]
            y[:, i] = state
    
    tl.store(Y_ptrs, y.to(tl.float16), mask=final_mask)

def chunk_scan(
    X: torch.Tensor,
    A: torch.Tensor, 
    B: torch.Tensor,
    chunk: int = 128,
    BD: int = 128
) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    
    device = X.device
    Y = torch.empty_like(X)
    
    num_chunks = L // chunk
    BLOCK_D = min(BD, triton.next_power_of_2(D))
    BLOCK_L = min(chunk, 128)
    
    if chunk <= 128 and D <= 512:
        grid = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_fused_kernel[grid](
            X, A, B, Y,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
        )
    else:
        State = torch.zeros((num_chunks + 1, D), dtype=torch.float32, device=device)
        
        grid_forward = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_forward_kernel[grid_forward](
            X, A, B, Y, State,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
            STORE_STATE=True,
        )
        
        grid_backward = (num_chunks * (D // BD + (D % BD > 0)),)
        _chunk_scan_backward_kernel[grid_backward](
            X, A, B, Y, State,
            X.stride(0), X.stride(1),
            L, D,
            chunk_size=chunk, BD=BD,
            BLOCK_L=BLOCK_L, BLOCK_D=BLOCK_D,
        )
    
    return Y
'''
        return {"code": code}