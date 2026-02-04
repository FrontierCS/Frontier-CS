#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>

class MySimulator : public Simulator {
private:
    int numThreads = 0;

    struct Grid {
        float minX, minY;
        float cellSize;
        int width, height;
        std::vector<int> cellOfParticle;
        std::vector<int> counts;
        std::vector<int> starts;      // size = numCells + 1
        std::vector<int> indices;     // sorted particle indices by cell
    };

    void buildGrid(const std::vector<Particle>& particles, float cellSize, Grid& grid) {
        size_t N = particles.size();
        if (N == 0) return;

        float minX = std::numeric_limits<float>::infinity();
        float minY = std::numeric_limits<float>::infinity();
        float maxX = -std::numeric_limits<float>::infinity();
        float maxY = -std::numeric_limits<float>::infinity();

        for (size_t i = 0; i < N; ++i) {
            const auto& p = particles[i];
            if (p.position.x < minX) minX = p.position.x;
            if (p.position.y < minY) minY = p.position.y;
            if (p.position.x > maxX) maxX = p.position.x;
            if (p.position.y > maxY) maxY = p.position.y;
        }

        // Small padding to be safe with numeric edges
        const float eps = 1e-6f;
        minX -= eps;
        minY -= eps;
        maxX += eps;
        maxY += eps;

        int width = std::max(1, int((maxX - minX) / cellSize) + 1);
        int height = std::max(1, int((maxY - minY) / cellSize) + 1);
        int numCells = width * height;

        grid.minX = minX;
        grid.minY = minY;
        grid.cellSize = cellSize;
        grid.width = width;
        grid.height = height;

        grid.cellOfParticle.assign(N, 0);
        grid.counts.assign(numCells, 0);
        grid.starts.assign(numCells + 1, 0);
        grid.indices.assign(N, 0);

        // Compute cell for each particle and counts
        for (size_t i = 0; i < N; ++i) {
            int cx = int(std::floor((particles[i].position.x - minX) / cellSize));
            int cy = int(std::floor((particles[i].position.y - minY) / cellSize));
            if (cx < 0) cx = 0; else if (cx >= width) cx = width - 1;
            if (cy < 0) cy = 0; else if (cy >= height) cy = height - 1;
            int cell = cy * width + cx;
            grid.cellOfParticle[i] = cell;
            grid.counts[cell]++;
        }

        // Prefix sum
        for (int c = 0; c < numCells; ++c) {
            grid.starts[c + 1] = grid.starts[c] + grid.counts[c];
        }

        // Fill indices
        std::vector<int> next = grid.starts;
        for (size_t i = 0; i < N; ++i) {
            int cell = grid.cellOfParticle[i];
            int pos = next[cell]++;
            grid.indices[pos] = (int)i;
        }
    }

public:
    void init(int numParticles, StepParameters params) override {
        int hwThreads = omp_get_max_threads();
        numThreads = hwThreads > 0 ? hwThreads : 1;
        omp_set_num_threads(numThreads);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const size_t N = particles.size();
        if (N == 0) return;
        newParticles.resize(N);

        const float r = params.cullRadius;
        const float r2 = r * r;

        // Build spatial grid
        Grid grid;
        buildGrid(particles, r, grid);

        const int W = grid.width;
        const int H = grid.height;
        const int numCells = W * H;

        int nt = numThreads;
        if (nt <= 0) nt = 1;

        std::vector<Vec2> localForces((size_t)nt * N);
        std::vector<Vec2> totalForce(N, Vec2(0.0f, 0.0f));

        // Neighbor offsets to cover each pair only once:
        // Within cell handled separately (i<j).
        // Cross-cell neighbor offsets: (1,-1), (1,0), (1,1), (0,1), (-1,1)
        const int nbrCount = 5;
        const int offX[nbrCount] = {1, 1, 1, 0, -1};
        const int offY[nbrCount] = {-1, 0, 1, 1, 1};

        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            Vec2* myForces = localForces.data() + (size_t)tid * N;
            for (size_t i = 0; i < N; ++i) {
                myForces[i] = Vec2(0.0f, 0.0f);
            }

            #pragma omp for schedule(dynamic, 1)
            for (int cell = 0; cell < numCells; ++cell) {
                int cx = cell % W;
                int cy = cell / W;

                int startA = grid.starts[cell];
                int endA = grid.starts[cell + 1];

                // Within-cell pairs
                for (int ia = startA; ia < endA; ++ia) {
                    int i = grid.indices[ia];
                    const Particle& pi = particles[i];
                    for (int ib = ia + 1; ib < endA; ++ib) {
                        int j = grid.indices[ib];
                        const Particle& pj = particles[j];

                        float dx = pj.position.x - pi.position.x;
                        float dy = pj.position.y - pi.position.y;
                        float dist2 = dx * dx + dy * dy;
                        if (dist2 < r2) {
                            Vec2 fij = computeForce(pi, pj, r);
                            myForces[i] += fij;
                            myForces[j] -= fij; // Newton's third law
                        }
                    }
                }

                // Cross-cell pairs with selected neighbor offsets
                for (int n = 0; n < nbrCount; ++n) {
                    int nx = cx + offX[n];
                    int ny = cy + offY[n];
                    if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
                    int cellB = ny * W + nx;

                    int startB = grid.starts[cellB];
                    int endB = grid.starts[cellB + 1];

                    for (int ia = startA; ia < endA; ++ia) {
                        int i = grid.indices[ia];
                        const Particle& pi = particles[i];
                        for (int ib = startB; ib < endB; ++ib) {
                            int j = grid.indices[ib];
                            const Particle& pj = particles[j];

                            float dx = pj.position.x - pi.position.x;
                            float dy = pj.position.y - pi.position.y;
                            float dist2 = dx * dx + dy * dy;
                            if (dist2 < r2) {
                                Vec2 fij = computeForce(pi, pj, r);
                                myForces[i] += fij;
                                myForces[j] -= fij;
                            }
                        }
                    }
                }
            }

            // Reduction of forces across threads
            #pragma omp for schedule(static)
            for (size_t i = 0; i < N; ++i) {
                Vec2 sum(0.0f, 0.0f);
                for (int t = 0; t < nt; ++t) {
                    sum += localForces[(size_t)t * N + i];
                }
                totalForce[i] = sum;
            }

            // Integrate positions/velocities
            #pragma omp for schedule(static)
            for (int i = 0; i < (int)N; ++i) {
                newParticles[i] = updateParticle(particles[i], totalForce[i], params.deltaTime);
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}