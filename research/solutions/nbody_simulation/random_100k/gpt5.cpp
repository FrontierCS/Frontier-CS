#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>

class MySimulator : public Simulator {
private:
    int numThreads;
    // Spatial grid structures
    std::vector<int> cellStart;
    std::vector<int> cellCount;
    std::vector<int> particleCell;
    std::vector<int> sortedIndices;
    // Task list for cell pair processing
    struct CellPair { int a, b; };
    std::vector<CellPair> tasks;
    // Per-thread force buffers
    std::vector<std::vector<Vec2>> threadForces;
    // Grid and step parameters
    float cellSizeScale = 0.5f; // cellSize = cullRadius * 0.5
    float lastCullRadius = -1.0f;
    int lastNumParticles = -1;

public:
    MySimulator() {
        numThreads = omp_get_max_threads();
    }

    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        lastNumParticles = numParticles;
        lastCullRadius = params.cullRadius;
        // Prepare per-thread buffers
        threadForces.resize(numThreads);
        for (int t = 0; t < numThreads; ++t) {
            threadForces[t].assign(numParticles, Vec2{0.0f, 0.0f});
        }
        // Reserve particle indexing buffers
        particleCell.assign(numParticles, 0);
        sortedIndices.assign(numParticles, 0);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = (int)particles.size();
        if (N == 0) return;

        if (lastNumParticles != N || lastCullRadius != params.cullRadius) {
            init(N, params);
        }

        // Compute bounding box
        float minX = particles[0].position.x, maxX = minX;
        float minY = particles[0].position.y, maxY = minY;
        for (int i = 1; i < N; ++i) {
            float x = particles[i].position.x;
            float y = particles[i].position.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }
        // Slight padding to avoid boundary clamping issues
        const float pad = 1e-4f;
        minX -= pad; minY -= pad;
        maxX += pad; maxY += pad;

        const float s = params.cullRadius;
        const float cellSize = std::max(1e-3f, s * cellSizeScale);
        const float invCell = 1.0f / cellSize;

        int nx = std::max(1, (int)std::ceil((maxX - minX) * invCell));
        int ny = std::max(1, (int)std::ceil((maxY - minY) * invCell));
        const int numCells = nx * ny;

        cellCount.assign(numCells, 0);
        cellStart.assign(numCells, 0);

        // Assign particles to cells and count
        for (int i = 0; i < N; ++i) {
            int cx = (int)std::floor((particles[i].position.x - minX) * invCell);
            int cy = (int)std::floor((particles[i].position.y - minY) * invCell);
            if (cx < 0) cx = 0; if (cx >= nx) cx = nx - 1;
            if (cy < 0) cy = 0; if (cy >= ny) cy = ny - 1;
            int c = cy * nx + cx;
            particleCell[i] = c;
            cellCount[c]++;
        }

        // Prefix sum for cellStart
        int sum = 0;
        for (int c = 0; c < numCells; ++c) {
            cellStart[c] = sum;
            sum += cellCount[c];
        }

        // Fill sortedIndices
        std::vector<int> writeHead = cellStart;
        for (int i = 0; i < N; ++i) {
            int c = particleCell[i];
            int idx = writeHead[c]++;
            sortedIndices[idx] = i;
        }

        // Build cell pair tasks
        tasks.clear();
        const int rCells = std::max(1, (int)std::ceil(s / cellSize));
        tasks.reserve((size_t)numCells * (2 * rCells + 1) * (2 * rCells + 1) / 2);
        for (int ay = 0; ay < ny; ++ay) {
            for (int ax = 0; ax < nx; ++ax) {
                int a = ay * nx + ax;
                for (int dy = 0; dy <= rCells; ++dy) {
                    int by = ay + dy;
                    if (by < 0 || by >= ny) continue;
                    int dxMin = -rCells;
                    int dxMax = rCells;
                    for (int dx = dxMin; dx <= dxMax; ++dx) {
                        if (dy == 0 && dx < 0) continue; // avoid duplicates; handle a==b separately
                        int bx = ax + dx;
                        if (bx < 0 || bx >= nx) continue;
                        int b = by * nx + bx;
                        tasks.push_back({a, b});
                    }
                }
            }
        }

        // Zero per-thread forces
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            auto &forces = threadForces[tid];
            std::fill(forces.begin(), forces.end(), Vec2{0.0f, 0.0f});
        }

        const float s2 = s * s;

        // Process tasks in parallel
        #pragma omp parallel for schedule(dynamic, 1)
        for (int ti = 0; ti < (int)tasks.size(); ++ti) {
            int tid = omp_get_thread_num();
            auto &forces = threadForces[tid];

            const int a = tasks[ti].a;
            const int b = tasks[ti].b;

            const int aStart = cellStart[a];
            const int aCount = cellCount[a];
            const int bStart = cellStart[b];
            const int bCount = cellCount[b];

            if (aCount == 0 || bCount == 0) continue;

            if (a == b) {
                for (int ia = 0; ia < aCount; ++ia) {
                    int idx_i = sortedIndices[aStart + ia];
                    const Particle &pi = particles[idx_i];
                    for (int ib = ia + 1; ib < bCount; ++ib) {
                        int idx_j = sortedIndices[bStart + ib];
                        const Particle &pj = particles[idx_j];

                        float dx = pj.position.x - pi.position.x;
                        float dy = pj.position.y - pi.position.y;
                        float dist2 = dx * dx + dy * dy;
                        if (dist2 >= s2) continue;

                        Vec2 fij = computeForce(pi, pj, s);
                        if (fij.x != 0.0f || fij.y != 0.0f) {
                            forces[idx_i] += fij;
                            forces[idx_j] -= fij;
                        }
                    }
                }
            } else {
                for (int ia = 0; ia < aCount; ++ia) {
                    int idx_i = sortedIndices[aStart + ia];
                    const Particle &pi = particles[idx_i];
                    for (int ib = 0; ib < bCount; ++ib) {
                        int idx_j = sortedIndices[bStart + ib];
                        const Particle &pj = particles[idx_j];

                        float dx = pj.position.x - pi.position.x;
                        float dy = pj.position.y - pi.position.y;
                        float dist2 = dx * dx + dy * dy;
                        if (dist2 >= s2) continue;

                        Vec2 fij = computeForce(pi, pj, s);
                        if (fij.x != 0.0f || fij.y != 0.0f) {
                            forces[idx_i] += fij;
                            forces[idx_j] -= fij;
                        }
                    }
                }
            }
        }

        // Reduce per-thread forces into a single array
        std::vector<Vec2> totalForces(N, Vec2{0.0f, 0.0f});
        for (int t = 0; t < numThreads; ++t) {
            auto &forces = threadForces[t];
            #pragma omp parallel for schedule(static)
            for (int i = 0; i < N; ++i) {
                totalForces[i] += forces[i];
            }
        }

        // Integrate particles
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; ++i) {
            newParticles[i] = updateParticle(particles[i], totalForces[i], params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}