#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <utility>

#ifdef __GNUC__
#include <parallel/algorithm>
#define PARALLEL_SORT __gnu_parallel::sort
#else
#define PARALLEL_SORT std::sort
#endif

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    std::vector<std::pair<int, int>> particle_cell_pairs;
    std::vector<int> cell_starts;

public:
    void init(int numParticles, StepParameters params) override {
        int max_threads = omp_get_max_threads();
        if (numThreads > max_threads) {
            numThreads = max_threads;
        }
        omp_set_num_threads(numThreads);
        particle_cell_pairs.reserve(numParticles);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = particles.size();
        if (N == 0) return;

        // 1. Find bounding box of particles in parallel
        float min_x = particles[0].position.x;
        float min_y = particles[0].position.y;
        float max_x = particles[0].position.x;
        float max_y = particles[0].position.y;
        
        #pragma omp parallel for reduction(min:min_x, min_y) reduction(max:max_x, max_y)
        for (int i = 1; i < N; ++i) {
            min_x = std::min(min_x, particles[i].position.x);
            min_y = std::min(min_y, particles[i].position.y);
            max_x = std::max(max_x, particles[i].position.x);
            max_y = std::max(max_y, particles[i].position.y);
        }

        // 2. Setup grid parameters
        const float cellSize = params.cullRadius;
        const float invCellSize = 1.0f / cellSize;
        
        const int gridWidth = static_cast<int>((max_x - min_x) * invCellSize) + 1;
        const int gridHeight = static_cast<int>((max_y - min_y) * invCellSize) + 1;
        const int numCells = gridWidth * gridHeight;

        // 3. Assign particles to grid cells
        particle_cell_pairs.resize(N);
        #pragma omp parallel for
        for (int i = 0; i < N; ++i) {
            const auto& p = particles[i];
            int cx = static_cast<int>((p.position.x - min_x) * invCellSize);
            int cy = static_cast<int>((p.position.y - min_y) * invCellSize);
            // Clamp to prevent out-of-bounds due to floating point inaccuracies
            cx = std::min(gridWidth - 1, cx);
            cy = std::min(gridHeight - 1, cy);
            particle_cell_pairs[i] = {cy * gridWidth + cx, i};
        }

        // 4. Sort particles based on their cell index to group them
        PARALLEL_SORT(particle_cell_pairs.begin(), particle_cell_pairs.end());

        // 5. Find the start index of each cell in the sorted list
        cell_starts.assign(numCells + 1, N);
        if (N > 0) {
            int last_cell = -1;
            for (int i = 0; i < N; ++i) {
                int current_cell = particle_cell_pairs[i].first;
                if (current_cell != last_cell) {
                    for (int c = last_cell + 1; c <= current_cell; ++c) {
                        cell_starts[c] = i;
                    }
                    last_cell = current_cell;
                }
            }
        } else {
             cell_starts.assign(numCells + 1, 0);
        }

        // 6. Compute forces in parallel
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < N; ++i) {
            const auto& pi = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int cx = static_cast<int>((pi.position.x - min_x) * invCellSize);
            int cy = static_cast<int>((pi.position.y - min_y) * invCellSize);
            cx = std::min(gridWidth - 1, cx);
            cy = std::min(gridHeight - 1, cy);

            for (int ny = cy - 1; ny <= cy + 1; ++ny) {
                for (int nx = cx - 1; nx <= cx + 1; ++nx) {
                    if (nx >= 0 && nx < gridWidth && ny >= 0 && ny < gridHeight) {
                        const int cell_id = ny * gridWidth + nx;
                        const int start_idx = cell_starts[cell_id];
                        const int end_idx = cell_starts[cell_id + 1];

                        for (int k = start_idx; k < end_idx; ++k) {
                            const int j_idx = particle_cell_pairs[k].second;
                            if (i != j_idx) {
                                total_force += computeForce(pi, particles[j_idx], params.cullRadius);
                            }
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(pi, total_force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}