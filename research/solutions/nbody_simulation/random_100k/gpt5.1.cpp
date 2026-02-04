#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>

class MySimulator : public Simulator {
private:
    int maxParticles = 0;
    int maxThreads = 1;

    // Per-thread force buffers: size = maxThreads * maxParticles
    std::vector<float> forceX;
    std::vector<float> forceY;

    // Spatial grid / hashing data
    std::vector<int> cellIndices;          // cell index per particle, size = numParticles
    std::vector<int> gridParticleIndices;  // particles sorted by cell, size = numParticles
    std::vector<int> cellCounts;           // particles per cell, size = numCells
    std::vector<int> cellStart;            // prefix sums, size = numCells + 1
    std::vector<int> cellOffsets;          // temp offsets for fill, size = numCells

public:
    void init(int numParticles, StepParameters params) override {
        // Fix OpenMP configuration
        omp_set_dynamic(0);              // disable dynamic adjustment
        maxThreads = omp_get_max_threads();
        omp_set_num_threads(maxThreads); // ensure parallel regions use this

        maxParticles = numParticles;
        forceX.assign(maxThreads * maxParticles, 0.0f);
        forceY.assign(maxThreads * maxParticles, 0.0f);

        cellIndices.resize(maxParticles);
        gridParticleIndices.resize(maxParticles);

        cellCounts.clear();
        cellStart.clear();
        cellOffsets.clear();
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = static_cast<int>(particles.size());
        if (n == 0) return;

        if (static_cast<int>(newParticles.size()) != n) {
            newParticles.resize(n);
        }

        // Resize buffers if particle count increased beyond initial
        if (n > maxParticles) {
            maxParticles = n;
            forceX.assign(maxThreads * maxParticles, 0.0f);
            forceY.assign(maxThreads * maxParticles, 0.0f);
            cellIndices.resize(maxParticles);
            gridParticleIndices.resize(maxParticles);
        } else {
            cellIndices.resize(n);
            gridParticleIndices.resize(n);
        }

        const float cullR = params.cullRadius;

        // If cull radius is non-positive, no forces act; just integrate with zero force.
        if (cullR <= 0.0f) {
            #pragma omp parallel for schedule(static)
            for (int i = 0; i < n; ++i) {
                Vec2 zero(0.0f, 0.0f);
                newParticles[i] = updateParticle(particles[i], zero, params.deltaTime);
            }
            return;
        }

        // Compute bounding box of particles (sequential - cheap)
        float minX = particles[0].position.x;
        float maxX = minX;
        float minY = particles[0].position.y;
        float maxY = minY;
        for (int i = 1; i < n; ++i) {
            const Vec2 &pos = particles[i].position;
            const float x = pos.x;
            const float y = pos.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        // Spatial grid configuration
        // Use cell size as a fraction of cullRadius to get reasonably fine grid.
        float cellSize = cullR * 0.125f; // cullRadius / 8
        if (cellSize < 1e-3f) {
            cellSize = std::max(cullR, 1e-3f);
        }
        const float invCellSize = 1.0f / cellSize;

        const float widthX = maxX - minX;
        const float widthY = maxY - minY;

        int gridW = std::max(1, static_cast<int>(std::ceil(widthX * invCellSize)));
        int gridH = std::max(1, static_cast<int>(std::ceil(widthY * invCellSize)));
        int numCells = gridW * gridH;

        cellCounts.assign(numCells, 0);
        cellStart.assign(numCells + 1, 0);
        cellOffsets.assign(numCells, 0);

        // First pass: assign each particle to a cell and count
        for (int i = 0; i < n; ++i) {
            const Vec2 &pos = particles[i].position;
            int cx = static_cast<int>((pos.x - minX) * invCellSize);
            int cy = static_cast<int>((pos.y - minY) * invCellSize);

            if (cx < 0) cx = 0;
            else if (cx >= gridW) cx = gridW - 1;
            if (cy < 0) cy = 0;
            else if (cy >= gridH) cy = gridH - 1;

            const int cell = cy * gridW + cx;
            cellIndices[i] = cell;
            cellCounts[cell]++;
        }

        // Prefix sums to get cell start indices
        int sum = 0;
        for (int c = 0; c < numCells; ++c) {
            cellStart[c] = sum;
            sum += cellCounts[c];
        }
        cellStart[numCells] = sum; // should be == n

        // Second pass: fill gridParticleIndices with particles grouped by cell
        for (int c = 0; c < numCells; ++c) {
            cellOffsets[c] = cellStart[c];
        }
        for (int i = 0; i < n; ++i) {
            const int cell = cellIndices[i];
            const int dst = cellOffsets[cell]++;
            gridParticleIndices[dst] = i;
        }

        const float cull2 = cullR * cullR;
        const int neighborRange = static_cast<int>(std::ceil(cullR / cellSize)) + 1;

        #pragma omp parallel
        {
            const int tid = omp_get_thread_num();
            const int T = omp_get_num_threads(); // should equal maxThreads

            float *fx = &forceX[tid * maxParticles];
            float *fy = &forceY[tid * maxParticles];

            // Zero thread-local force buffers for active particles
            for (int i2 = 0; i2 < n; ++i2) {
                fx[i2] = 0.0f;
                fy[i2] = 0.0f;
            }

            // Compute pairwise forces using spatial grid, each unordered pair exactly once
            #pragma omp for schedule(dynamic)
            for (int cell = 0; cell < numCells; ++cell) {
                const int cy = cell / gridW;
                const int cx = cell - cy * gridW;

                const int iBegin = cellStart[cell];
                const int iEnd   = cellStart[cell + 1];
                if (iBegin >= iEnd) continue;

                const int nyMin = std::max(0, cy - neighborRange);
                const int nyMax = std::min(gridH - 1, cy + neighborRange);
                const int nxMin0 = std::max(0, cx - neighborRange);
                const int nxMax0 = std::min(gridW - 1, cx + neighborRange);

                for (int ny = nyMin; ny <= nyMax; ++ny) {
                    const int rowBase = ny * gridW;
                    for (int nx = nxMin0; nx <= nxMax0; ++nx) {
                        const int cell2 = rowBase + nx;
                        if (cell2 < cell) continue; // avoid double counting cell pairs

                        const int jBegin = cellStart[cell2];
                        const int jEnd   = cellStart[cell2 + 1];
                        if (jBegin >= jEnd) continue;

                        if (cell2 == cell) {
                            // Pairs within same cell: i<j
                            for (int ia = iBegin; ia < iEnd; ++ia) {
                                const int idxI = gridParticleIndices[ia];
                                const Particle &pi = particles[idxI];
                                for (int jb = ia + 1; jb < iEnd; ++jb) {
                                    const int idxJ = gridParticleIndices[jb];
                                    const Particle &pj = particles[idxJ];

                                    const float dx = pj.position.x - pi.position.x;
                                    const float dy = pj.position.y - pi.position.y;
                                    const float dist2 = dx * dx + dy * dy;
                                    if (dist2 < cull2) {
                                        const Vec2 f = computeForce(pi, pj, cullR);
                                        fx[idxI] += f.x;
                                        fy[idxI] += f.y;
                                        fx[idxJ] -= f.x;
                                        fy[idxJ] -= f.y;
                                    }
                                }
                            }
                        } else {
                            // Pairs between different cells: all combinations
                            for (int ia = iBegin; ia < iEnd; ++ia) {
                                const int idxI = gridParticleIndices[ia];
                                const Particle &pi = particles[idxI];
                                for (int jb = jBegin; jb < jEnd; ++jb) {
                                    const int idxJ = gridParticleIndices[jb];
                                    const Particle &pj = particles[idxJ];

                                    const float dx = pj.position.x - pi.position.x;
                                    const float dy = pj.position.y - pi.position.y;
                                    const float dist2 = dx * dx + dy * dy;
                                    if (dist2 < cull2) {
                                        const Vec2 f = computeForce(pi, pj, cullR);
                                        fx[idxI] += f.x;
                                        fy[idxI] += f.y;
                                        fx[idxJ] -= f.x;
                                        fy[idxJ] -= f.y;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Barrier is implicit at the end of the omp for above (no nowait)

            // Reduce per-thread forces and integrate particles
            #pragma omp for schedule(static)
            for (int i2 = 0; i2 < n; ++i2) {
                float fxTotal = 0.0f;
                float fyTotal = 0.0f;
                for (int t = 0; t < T; ++t) {
                    fxTotal += forceX[t * maxParticles + i2];
                    fyTotal += forceY[t * maxParticles + i2];
                }
                Vec2 totalForce(fxTotal, fyTotal);
                newParticles[i2] = updateParticle(particles[i2], totalForce, params.deltaTime);
            }
        } // end parallel
    }
};

// Factory function - must be implemented
Simulator* createSimulator() {
    return new MySimulator();
}