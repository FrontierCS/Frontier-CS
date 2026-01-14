# Dockerfile for triton-tlx with nvcc support
# Build: docker build -t andylizf/triton-tlx:tlx-nv-cu122-nvcc -f Dockerfile .
# Push: docker push andylizf/triton-tlx:tlx-nv-cu122-nvcc

FROM andylizf/triton-tlx:tlx-nv-cu122

# Install full CUDA toolkit for flashinfer JIT compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cuda-toolkit-12-2 \
    && rm -rf /var/lib/apt/lists/*

# Verify nvcc is available
RUN /usr/local/cuda-12.2/bin/nvcc --version

# Add nvcc to PATH
ENV PATH="/usr/local/cuda-12.2/bin:${PATH}"
