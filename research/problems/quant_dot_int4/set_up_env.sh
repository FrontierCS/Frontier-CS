#!/usr/bin/env bash
set -euo pipefail

# Set up environment for GEMM optimization problem
echo "Setting up environment for GEMM optimization problem..."

# The Triton image should already have the necessary dependencies
# Just verify that Triton and PyTorch are available
python3 -c "import torch; import triton; print(f'PyTorch version: {torch.__version__}'); print(f'Triton version: {triton.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

echo "Environment setup complete"
