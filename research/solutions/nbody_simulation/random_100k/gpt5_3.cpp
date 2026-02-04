#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstring>

class MySimulator : public Simulator {
private:
    int numThreads = 0;
    int lastN = 0;

    // Thread-local force buffers: forces[thread][i]
    std::vector<std::vector<Vec2>> threadForces;

    // Grid buffers (reused across steps)
    std::vector<int> cellCounts;
    std::vector<int> cellStarts;     // size = numCells + 1
    std::vector<int> cellIndices;    // size = N

    // Neighbor offset structure
    struct Offset {
        int dx, dy;
        float minDist2;
        bool self;
    };
    std::vector<Offset> neighborOffsets;

    // Parameters for grid
    float cellSize = 1.0f;
    int R = 1;  // radius in cells
    int gridX = 0, gridY = 0; // number of cells in X and Y

    // Expand or allocate force buffers when N or threads changes
    void ensureForceBuffers(int N) {
        int T = numThreads;
        if ((int)threadForces.size() != T || lastN != N) {
            threadForces.clear();
            threadForces.resize(T);
            for (int t = 0; t < T; ++t) {
                threadForces[t].assign(N, Vec2{0.0f, 0.0f});
            }
            lastN = N;
        } else {
            // zero buffers
            #pragma omp parallel for schedule(static)
            for (int t = 0; t < T; ++t) {
                std::fill(threadForces[t].begin(), threadForces[t].end(), Vec2{0.0f, 0.0f});
            }
        }
    }

    // Build neighbor offsets for current R and cellSize and cullRadius
    void buildNeighborOffsets(float cullRadius) {
        neighborOffsets.clear();
        neighborOffsets.reserve((2 * R + 1) * (2 * R + 1));

        float s = cellSize;
        float r2 = cullRadius * cullRadius;

        for (int dx = 0; dx <= R; ++dx) {
            for (int dy = -R; dy <= R; ++dy) {
                // Only unique pairs: (dx>0, any dy) or (dx==0 && dy>=0)
                if (dx == 0 && dy < 0) continue;

                int adx = dx;
                int ady = std::abs(dy);
                float minDx = std::max(0, adx - 1) * s;
                float minDy = std::max(0, ady - 1) * s;
                float minD2 = minDx * minDx + minDy * minDy;

                if (minD2 <= r2) {
                    Offset off;
                    off.dx = dx;
                    off.dy = dy;
                    off.minDist2 = minD2;
                    off.self = (dx == 0 && dy == 0);
                    neighborOffsets.push_back(off);
                }
            }
        }
    }

    // Compute grid bounds and map particles into cells
    void buildGrid(const std::vector<Particle>& particles, float cullRadius,
                   float& minX, float& minY) {
        const int N = (int)particles.size();

        // Determine bounding box
        float maxX = -1e30f, maxY = -1e30f;
        minX = 1e30f; minY = 1e30f;
        for (int i = 0; i < N; ++i) {
            float x = particles[i].position.x;
            float y = particles[i].position.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        // Slight padding to ensure boundary particles fit
        float pad = 1e-3f;
        minX -= pad; minY -= pad;
        maxX += pad; maxY += pad;

        // Define grid: choose cell size relative to cullRadius
        // Using k = 5 (cellSize = r / 5) for better pruning
        cellSize = std::max(cullRadius / 5.0f, 1e-3f);
        R = (int)std::ceil(cullRadius / cellSize);

        gridX = std::max(1, (int)std::ceil((maxX - minX) / cellSize));
        gridY = std::max(1, (int)std::ceil((maxY - minY) / cellSize));
        int numCells = gridX * gridY;

        if ((int)cellCounts.size() != numCells) {
            cellCounts.assign(numCells, 0);
            cellStarts.assign(numCells + 1, 0);
        } else {
            std::fill(cellCounts.begin(), cellCounts.end(), 0);
            std::fill(cellStarts.begin(), cellStarts.end(), 0);
        }

        if ((int)cellIndices.size() != N) {
            cellIndices.resize(N);
        }

        // Count particles per cell
        for (int i = 0; i < N; ++i) {
            int ix = (int)std::floor((particles[i].position.x - minX) / cellSize);
            int iy = (int)std::floor((particles[i].position.y - minY) / cellSize);
            if (ix < 0) ix = 0; else if (ix >= gridX) ix = gridX - 1;
            if (iy < 0) iy = 0; else if (iy >= gridY) iy = gridY - 1;
            int cid = iy * gridX + ix;
            cellCounts[cid]++;
        }

        // Prefix sums for starts
        int sum = 0;
        for (int c = 0; c < numCells; ++c) {
            cellStarts[c] = sum;
            sum += cellCounts[c];
        }
        cellStarts[numCells] = sum;

        // Temporary write positions
        std::vector<int> writePos = cellStarts;

        // Assign particle indices to cells
        for (int i = 0; i < N; ++i) {
            int ix = (int)std::floor((particles[i].position.x - minX) / cellSize);
            int iy = (int)std::floor((particles[i].position.y - minY) / cellSize);
            if (ix < 0) ix = 0; else if (ix >= gridX) ix = gridX - 1;
            if (iy < 0) iy = 0; else if (iy >= gridY) iy = gridY - 1;
            int cid = iy * gridX + ix;
            cellIndices[writePos[cid]++] = i;
        }

        // Build neighbor offsets for this cell configuration and cullRadius
        buildNeighborOffsets(cullRadius);
    }

public:
    void init(int numParticles, StepParameters params) override {
        numThreads = omp_get_max_threads();
        omp_set_num_threads(numThreads);
        ensureForceBuffers(numParticles);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = (int)particles.size();
        if (N == 0) return;

        if (numThreads <= 0) {
            numThreads = omp_get_max_threads();
            omp_set_num_threads(numThreads);
        }
        ensureForceBuffers(N);

        // Build grid
        float minX = 0.0f, minY = 0.0f;
        buildGrid(particles, params.cullRadius, minX, minY);

        // Prepare list of cell-pair tasks to improve load balancing
        struct Task {
            int aStart, aEnd;
            int bStart, bEnd;
            bool self;
        };
        std::vector<Task> tasks;
        tasks.reserve(gridX * gridY * (int)neighborOffsets.size());

        int numCells = gridX * gridY;
        for (int ay = 0; ay < gridY; ++ay) {
            for (int ax = 0; ax < gridX; ++ax) {
                int aId = ay * gridX + ax;
                int aStart = cellStarts[aId];
                int aEnd = cellStarts[aId + 1];
                int aCount = aEnd - aStart;
                if (aCount == 0) continue;

                for (const auto& off : neighborOffsets) {
                    int bx = ax + off.dx;
                    int by = ay + off.dy;
                    if (bx < 0 || bx >= gridX || by < 0 || by >= gridY) continue;
                    int bId = by * gridX + bx;

                    int bStart = cellStarts[bId];
                    int bEnd = cellStarts[bId + 1];
                    int bCount = bEnd - bStart;
                    if (bCount == 0) continue;

                    Task task;
                    task.aStart = aStart;
                    task.aEnd = aEnd;
                    if (off.self) {
                        task.bStart = aStart;
                        task.bEnd = aEnd;
                        task.self = true;
                    } else {
                        task.bStart = bStart;
                        task.bEnd = bEnd;
                        task.self = false;
                    }
                    tasks.push_back(task);
                }
            }
        }

        // Constants
        const float r = params.cullRadius;
        const float r2 = r * r;
        const float dt = params.deltaTime;
        const float epsClose = 1e-3f;
        const float epsClose2 = epsClose * epsClose;
        const float minDistClamp = 1e-1f;
        const float G = 0.01f;
        const float r75 = r * 0.75f;
        const float r25 = r * 0.25f;

        const Particle* P = particles.data();

        // Parallel process tasks, accumulate into thread-local forces
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            Vec2* localF = threadForces[tid].data();

            #pragma omp for schedule(dynamic, 1)
            for (int ti = 0; ti < (int)tasks.size(); ++ti) {
                const Task& task = tasks[ti];

                if (task.self) {
                    // Pairs within the same cell: i < j
                    for (int ia = task.aStart; ia < task.aEnd; ++ia) {
                        int i = cellIndices[ia];
                        const Particle& pi = P[i];
                        float xi = pi.position.x;
                        float yi = pi.position.y;
                        float mi = pi.mass;

                        for (int ja = ia + 1; ja < task.aEnd; ++ja) {
                            int j = cellIndices[ja];
                            const Particle& pj = P[j];

                            float dx = pj.position.x - xi;
                            float dy = pj.position.y - yi;
                            float d2 = dx * dx + dy * dy;
                            if (d2 > r2 || d2 < epsClose2) continue;

                            float dist = std::sqrt(d2);
                            float invDist = 1.0f / dist;
                            float dirx = dx * invDist;
                            float diry = dy * invDist;

                            float distUsed = (dist < minDistClamp) ? minDistClamp : dist;
                            float mag = (G * mi * pj.mass) / (distUsed * distUsed);
                            if (dist > r75) {
                                float decay = 1.0f - (dist - r75) / r25;
                                mag *= decay;
                            }

                            float fx = dirx * mag;
                            float fy = diry * mag;

                            localF[i].x += fx;
                            localF[i].y += fy;
                            localF[j].x -= fx;
                            localF[j].y -= fy;
                        }
                    }
                } else {
                    // Cross-cell pairs: all i in A against all j in B
                    for (int ia = task.aStart; ia < task.aEnd; ++ia) {
                        int i = cellIndices[ia];
                        const Particle& pi = P[i];
                        float xi = pi.position.x;
                        float yi = pi.position.y;
                        float mi = pi.mass;

                        for (int jb = task.bStart; jb < task.bEnd; ++jb) {
                            int j = cellIndices[jb];
                            const Particle& pj = P[j];

                            float dx = pj.position.x - xi;
                            float dy = pj.position.y - yi;
                            float d2 = dx * dx + dy * dy;
                            if (d2 > r2 || d2 < epsClose2) continue;

                            float dist = std::sqrt(d2);
                            float invDist = 1.0f / dist;
                            float dirx = dx * invDist;
                            float diry = dy * invDist;

                            float distUsed = (dist < minDistClamp) ? minDistClamp : dist;
                            float mag = (G * mi * pj.mass) / (distUsed * distUsed);
                            if (dist > r75) {
                                float decay = 1.0f - (dist - r75) / r25;
                                mag *= decay;
                            }

                            float fx = dirx * mag;
                            float fy = diry * mag;

                            localF[i].x += fx;
                            localF[i].y += fy;
                            localF[j].x -= fx;
                            localF[j].y -= fy;
                        }
                    }
                }
            }
        }

        // Reduce forces across threads and update particles
        newParticles.resize(N);
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; ++i) {
            Vec2 totalF{0.0f, 0.0f};
            for (int t = 0; t < numThreads; ++t) {
                totalF.x += threadForces[t][i].x;
                totalF.y += threadForces[t][i].y;
            }
            newParticles[i] = updateParticle(particles[i], totalF, dt);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}