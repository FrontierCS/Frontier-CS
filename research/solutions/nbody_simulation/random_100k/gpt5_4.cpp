#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

class MySimulator : public Simulator {
private:
    int numThreads = 0;

    // Persistent buffers to avoid reallocations
    std::vector<int> cellId;
    std::vector<int> counts;
    std::vector<int> cellStart;
    std::vector<int> offsets;
    std::vector<int> sortedIndices;

    // Thread-local force accumulation buffers
    std::vector<std::vector<Vec2>> threadForces;

    // Precomputed neighbor offsets for current cellSize and cullRadius
    std::vector<std::pair<int,int>> neighborOffsets;

    // Grid state
    float cellSize = 1.0f;
    int gridW = 0, gridH = 0;
    float minX = 0.0f, minY = 0.0f;

    void ensureForceBuffers(size_t n) {
        if (numThreads <= 0) {
            numThreads = omp_get_max_threads();
        }
        threadForces.resize(numThreads);
        for (int t = 0; t < numThreads; ++t) {
            if (threadForces[t].size() != n) {
                threadForces[t].assign(n, Vec2(0.0f, 0.0f));
            } else {
                std::fill(threadForces[t].begin(), threadForces[t].end(), Vec2(0.0f, 0.0f));
            }
        }
    }

    void precomputeNeighborOffsets(float cullRadius) {
        neighborOffsets.clear();
        int k = (int)std::ceil(cullRadius / cellSize);
        if (k < 0) k = 0;

        float s = cellSize;
        float r2 = cullRadius * cullRadius;

        // Only include offsets where neighbor cell index is "greater" to avoid duplicates
        for (int dy = -k; dy <= k; ++dy) {
            for (int dx = 0; dx <= k; ++dx) {
                if (dx == 0 && dy <= 0) continue; // skip self and duplicates (dx>0) or (dx==0 and dy>0)
                int adx = std::abs(dx);
                int ady = std::abs(dy);
                float minDx = (adx <= 1) ? 0.0f : (float)(adx - 1) * s;
                float minDy = (ady <= 1) ? 0.0f : (float)(ady - 1) * s;
                float minDist2 = minDx * minDx + minDy * minDy;
                if (minDist2 <= r2) {
                    neighborOffsets.emplace_back(dx, dy);
                }
            }
        }
    }

    void buildGrid(const std::vector<Particle> &particles, float cullRadius) {
        size_t n = particles.size();
        if (n == 0) {
            gridW = gridH = 0;
            return;
        }

        // Compute bounding box
        float localMinX = std::numeric_limits<float>::infinity();
        float localMinY = std::numeric_limits<float>::infinity();
        float localMaxX = -std::numeric_limits<float>::infinity();
        float localMaxY = -std::numeric_limits<float>::infinity();

        #pragma omp parallel
        {
            float tminx = localMinX;
            float tminy = localMinY;
            float tmaxx = localMaxX;
            float tmaxy = localMaxY;

            #pragma omp for nowait
            for (int i = 0; i < (int)n; ++i) {
                const auto &p = particles[i];
                if (p.position.x < tminx) tminx = p.position.x;
                if (p.position.y < tminy) tminy = p.position.y;
                if (p.position.x > tmaxx) tmaxx = p.position.x;
                if (p.position.y > tmaxy) tmaxy = p.position.y;
            }

            #pragma omp critical
            {
                if (tminx < localMinX) localMinX = tminx;
                if (tminy < localMinY) localMinY = tminy;
                if (tmaxx > localMaxX) localMaxX = tmaxx;
                if (tmaxy > localMaxY) localMaxY = tmaxy;
            }
        }

        // Set cell size relative to cullRadius. Smaller is better up to a point.
        // Choose r/10, but clamp to at least 2.0 for stability and performance.
        float desiredCellSize = std::max(2.0f, cullRadius / 10.0f);
        cellSize = desiredCellSize;

        // Add a small margin
        const float eps = 1e-3f;
        minX = localMinX - eps;
        minY = localMinY - eps;
        float maxX = localMaxX + eps;
        float maxY = localMaxY + eps;

        int w = (int)std::max(1, (int)std::floor((maxX - minX) / cellSize) + 1);
        int h = (int)std::max(1, (int)std::floor((maxY - minY) / cellSize) + 1);
        gridW = w;
        gridH = h;
        size_t nCells = (size_t)w * (size_t)h;

        // Allocate grid arrays
        cellId.resize(n);
        counts.assign(nCells, 0);
        cellStart.resize(nCells + 1);
        offsets.resize(nCells);
        sortedIndices.resize(n);

        // Map particles to cells
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < (int)n; ++i) {
            float fx = (particles[i].position.x - minX) / cellSize;
            float fy = (particles[i].position.y - minY) / cellSize;
            int ix = (int)std::floor(fx);
            int iy = (int)std::floor(fy);
            if (ix < 0) ix = 0; else if (ix >= w) ix = w - 1;
            if (iy < 0) iy = 0; else if (iy >= h) iy = h - 1;
            int cid = ix + iy * w;
            cellId[i] = cid;
        }

        // Count particles per cell
        for (size_t i = 0; i < n; ++i) {
            counts[cellId[i]]++;
        }

        // Compute prefix sums
        cellStart[0] = 0;
        for (size_t c = 0; c < nCells; ++c) {
            cellStart[c + 1] = cellStart[c] + counts[c];
        }

        // Setup offsets for insertion
        for (size_t c = 0; c < nCells; ++c) {
            offsets[c] = cellStart[c];
        }

        // Fill sortedIndices
        for (size_t i = 0; i < n; ++i) {
            int cid = cellId[i];
            int pos = offsets[cid]++;
            sortedIndices[pos] = (int)i;
        }

        // Precompute neighbor offsets for current grid configuration
        precomputeNeighborOffsets(cullRadius);
    }

public:
    void init(int numParticles, StepParameters params) override {
        numThreads = omp_get_max_threads();
        omp_set_num_threads(numThreads);

        // Prepare persistent buffers
        cellId.clear();
        counts.clear();
        cellStart.clear();
        offsets.clear();
        sortedIndices.clear();
        threadForces.clear();
        neighborOffsets.clear();
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        size_t n = particles.size();
        if (n == 0) return;

        // Build grid
        buildGrid(particles, params.cullRadius);

        // Prepare thread-local force accumulators
        ensureForceBuffers(n);

        float r2 = params.cullRadius * params.cullRadius;
        float cullRadius = params.cullRadius;

        size_t nCells = (size_t)gridW * (size_t)gridH;

        // Pairwise interactions using symmetric accumulation
        #pragma omp parallel for schedule(dynamic, 1)
        for (int cell = 0; cell < (int)nCells; ++cell) {
            int tid = omp_get_thread_num();
            auto &lf = threadForces[tid];

            int ix = cell % gridW;
            int iy = cell / gridW;

            int startA = cellStart[cell];
            int endA = cellStart[cell + 1];

            // Intra-cell interactions (i < j)
            for (int a = startA; a < endA; ++a) {
                int iIdx = sortedIndices[a];
                const Vec2 pi_pos = particles[iIdx].position;
                for (int b = a + 1; b < endA; ++b) {
                    int jIdx = sortedIndices[b];
                    const Vec2 pj_pos = particles[jIdx].position;

                    float dx = pj_pos.x - pi_pos.x;
                    float dy = pj_pos.y - pi_pos.y;
                    float d2 = dx * dx + dy * dy;
                    if (d2 > r2) continue;

                    Vec2 f = computeForce(particles[iIdx], particles[jIdx], cullRadius);
                    if (f.x != 0.0f || f.y != 0.0f) {
                        lf[iIdx] += f;
                        lf[jIdx] -= f;
                    }
                }
            }

            // Inter-cell interactions using precomputed neighbor offsets
            for (const auto &d : neighborOffsets) {
                int jx = ix + d.first;
                int jy = iy + d.second;
                if ((unsigned)jx >= (unsigned)gridW || (unsigned)jy >= (unsigned)gridH) continue;

                int neighborCell = jx + jy * gridW;

                int startB = cellStart[neighborCell];
                int endB = cellStart[neighborCell + 1];

                for (int a = startA; a < endA; ++a) {
                    int iIdx = sortedIndices[a];
                    const Vec2 pi_pos = particles[iIdx].position;
                    for (int b = startB; b < endB; ++b) {
                        int jIdx = sortedIndices[b];
                        const Vec2 pj_pos = particles[jIdx].position;

                        float dx = pj_pos.x - pi_pos.x;
                        float dy = pj_pos.y - pi_pos.y;
                        float d2 = dx * dx + dy * dy;
                        if (d2 > r2) continue;

                        Vec2 f = computeForce(particles[iIdx], particles[jIdx], cullRadius);
                        if (f.x != 0.0f || f.y != 0.0f) {
                            lf[iIdx] += f;
                            lf[jIdx] -= f;
                        }
                    }
                }
            }
        }

        // Reduce thread-local forces and update particles
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < (int)n; ++i) {
            Vec2 totalF(0.0f, 0.0f);
            for (int t = 0; t < numThreads; ++t) {
                totalF += threadForces[t][i];
            }
            newParticles[i] = updateParticle(particles[i], totalF, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}