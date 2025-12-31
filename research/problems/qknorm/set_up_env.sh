#!/usr/bin/env bash
set -euo pipefail

# Set up environment for qknorm optimization problem
echo "Setting up environment for qknorm optimization problem..."

# Install flashinfer if not available
if ! python3 -c "import flashinfer" 2>/dev/null; then
    echo "Installing flashinfer..."
    pip install flashinfer-python --extra-index-url https://flashinfer.ai/whl/cu122/torch2.4/
fi

# Verify that PyTorch and flashinfer are available
python3 -c "import torch; import flashinfer; print(f'PyTorch version: {torch.__version__}'); print(f'flashinfer available: {flashinfer.__version__ if hasattr(flashinfer, \"__version__\") else \"yes\"}'); print(f'CUDA available: {torch.cuda.is_available()}')"

echo "Environment setup complete"
