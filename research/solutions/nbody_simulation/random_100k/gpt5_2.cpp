#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cfloat>

class MySimulator : public Simulator {
private:
    int numThreads = 0;
    int N = 0;

    // Persistent buffers
    std::vector<int> particleCellID;      // size N
    std::vector<int> cellStarts;          // size numCells + 1 (per step)
    std::vector<int> cellCounts;          // size numCells (per step)
    std::vector<int> sortedIndices;       // size N (per step)

    // Thread-local force accumulators: size numThreads * N
    std::vector<float> localFx;
    std::vector<float> localFy;

    float cellFactor = 3.0f; // number of cells per cullRadius

public:
    void init(int numParticles, StepParameters params) override {
        N = numParticles;
        numThreads = std::max(1, omp_get_max_threads());
        omp_set_num_threads(numThreads);

        particleCellID.assign(N, 0);
        sortedIndices.resize(N);

        localFx.assign((size_t)numThreads * (size_t)N, 0.0f);
        localFy.assign((size_t)numThreads * (size_t)N, 0.0f);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        if (particles.empty()) return;

        const float r = params.cullRadius;
        const float r2 = r * r;
        float minX = FLT_MAX, minY = FLT_MAX;
        float maxX = -FLT_MAX, maxY = -FLT_MAX;

        // Determine bounding box
        #pragma omp parallel for reduction(min:minX,minY) reduction(max:maxX,maxY) schedule(static)
        for (int i = 0; i < (int)particles.size(); ++i) {
            const auto &p = particles[i];
            if (p.position.x < minX) minX = p.position.x;
            if (p.position.y < minY) minY = p.position.y;
            if (p.position.x > maxX) maxX = p.position.x;
            if (p.position.y > maxY) maxY = p.position.y;
        }

        const float eps = 1e-3f;
        minX -= eps; minY -= eps;
        maxX += eps; maxY += eps;

        float cellSize = std::max(r / cellFactor, 1e-3f);
        int gridNx = std::max(1, (int)((maxX - minX) / cellSize) + 1);
        int gridNy = std::max(1, (int)((maxY - minY) / cellSize) + 1);
        int numCells = gridNx * gridNy;
        int k = std::max(1, (int)std::ceil(r / cellSize));

        // Thread-local counts per cell to avoid atomics
        std::vector<int> localCounts((size_t)numThreads * (size_t)numCells, 0);
        cellCounts.assign(numCells, 0);
        cellStarts.resize(numCells + 1);

        // Compute cell IDs and local counts
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            int *lc = localCounts.data() + (size_t)tid * (size_t)numCells;

            #pragma omp for schedule(static)
            for (int i = 0; i < N; ++i) {
                const auto &p = particles[i];
                int ix = (int)((p.position.x - minX) / cellSize);
                int iy = (int)((p.position.y - minY) / cellSize);
                if (ix < 0) ix = 0; else if (ix >= gridNx) ix = gridNx - 1;
                if (iy < 0) iy = 0; else if (iy >= gridNy) iy = gridNy - 1;
                int cid = iy * gridNx + ix;
                particleCellID[i] = cid;
                lc[cid] += 1;
            }
        }

        // Reduce counts across threads
        for (int c = 0; c < numCells; ++c) {
            int sum = 0;
            for (int t = 0; t < numThreads; ++t) {
                sum += localCounts[(size_t)t * (size_t)numCells + (size_t)c];
            }
            cellCounts[c] = sum;
        }

        // Exclusive prefix sum for cell starts
        int total = 0;
        for (int c = 0; c < numCells; ++c) {
            cellStarts[c] = total;
            total += cellCounts[c];
        }
        cellStarts[numCells] = total;

        // Compute thread-specific starting offsets per cell
        std::vector<int> threadCellStart((size_t)numThreads * (size_t)numCells, 0);
        for (int c = 0; c < numCells; ++c) {
            int base = cellStarts[c];
            int accum = 0;
            for (int t = 0; t < numThreads; ++t) {
                int cnt = localCounts[(size_t)t * (size_t)numCells + (size_t)c];
                threadCellStart[(size_t)t * (size_t)numCells + (size_t)c] = base + accum;
                accum += cnt;
            }
        }

        // Fill sortedIndices per cell (stable within thread)
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            int* writePtr = threadCellStart.data() + (size_t)tid * (size_t)numCells;

            #pragma omp for schedule(static)
            for (int i = 0; i < N; ++i) {
                int cid = particleCellID[i];
                int pos = writePtr[cid]++;
                sortedIndices[pos] = i;
            }
        }

        // Zero thread-local forces
        std::fill(localFx.begin(), localFx.end(), 0.0f);
        std::fill(localFy.begin(), localFy.end(), 0.0f);

        // Pairwise interactions: process each cell with neighbors to avoid double counting
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            float* fx = localFx.data() + (size_t)tid * (size_t)N;
            float* fy = localFy.data() + (size_t)tid * (size_t)N;

            #pragma omp for schedule(dynamic, 1)
            for (int c = 0; c < numCells; ++c) {
                int cx = c % gridNx;
                int cy = c / gridNx;

                int cStart = cellStarts[c];
                int cEnd   = cellStarts[c + 1];

                // Interactions within the same cell
                for (int idxA = cStart; idxA < cEnd; ++idxA) {
                    int i = sortedIndices[idxA];
                    const Particle &pi = particles[i];
                    float pix = pi.position.x;
                    float piy = pi.position.y;

                    for (int idxB = idxA + 1; idxB < cEnd; ++idxB) {
                        int j = sortedIndices[idxB];
                        const Particle &pj = particles[j];

                        float dx = pj.position.x - pix;
                        float dy = pj.position.y - piy;
                        float d2 = dx * dx + dy * dy;
                        if (d2 > r2) continue;

                        Vec2 fi = computeForce(pi, pj, r);
                        fx[i] += fi.x; fy[i] += fi.y;
                        fx[j] -= fi.x; fy[j] -= fi.y;
                    }
                }

                // Interactions with neighboring cells (half-plane to avoid duplicate pairs)
                for (int ox = 0; ox <= k; ++ox) {
                    for (int oy = -k; oy <= k; ++oy) {
                        if (ox == 0 && oy < 0) continue; // ensure unique pairs
                        if (ox == 0 && oy == 0) continue; // skip self, already handled

                        int nx = cx + ox;
                        int ny = cy + oy;
                        if (nx < 0 || nx >= gridNx || ny < 0 || ny >= gridNy) continue;

                        int nc = ny * gridNx + nx;
                        int nStart = cellStarts[nc];
                        int nEnd   = cellStarts[nc + 1];

                        for (int idxA = cStart; idxA < cEnd; ++idxA) {
                            int i = sortedIndices[idxA];
                            const Particle &pi = particles[i];
                            float pix = pi.position.x;
                            float piy = pi.position.y;

                            for (int idxB = nStart; idxB < nEnd; ++idxB) {
                                int j = sortedIndices[idxB];
                                const Particle &pj = particles[j];

                                float dx = pj.position.x - pix;
                                float dy = pj.position.y - piy;
                                float d2 = dx * dx + dy * dy;
                                if (d2 > r2) continue;

                                Vec2 fi = computeForce(pi, pj, r);
                                fx[i] += fi.x; fy[i] += fi.y;
                                fx[j] -= fi.x; fy[j] -= fi.y;
                            }
                        }
                    }
                }
            }
        }

        // Reduce forces across threads and integrate
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; ++i) {
            float sx = 0.0f, sy = 0.0f;
            for (int t = 0; t < numThreads; ++t) {
                sx += localFx[(size_t)t * (size_t)N + (size_t)i];
                sy += localFy[(size_t)t * (size_t)N + (size_t)i];
            }
            Vec2 force(sx, sy);
            newParticles[i] = updateParticle(particles[i], force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}