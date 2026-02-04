#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>

class MySimulator : public Simulator {
private:
    int numThreads = 16;

    // Persistent buffers to avoid reallocations in each simulation step
    std::vector<std::pair<int, int>> particle_cell_map;
    std::vector<int> sorted_particle_indices;
    std::vector<int> cell_starts;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        // Resize persistent buffers only if the number of particles changes
        if (particle_cell_map.size() != (size_t)numParticles) {
            particle_cell_map.resize(numParticles);
            sorted_particle_indices.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = particles.size();
        if (n == 0) return;

        // Step 1: Compute the bounding box of all particles in parallel.
        float min_x = particles[0].position.x;
        float max_x = particles[0].position.x;
        float min_y = particles[0].position.y;
        float max_y = particles[0].position.y;

        #pragma omp parallel for reduction(min:min_x) reduction(max:max_x) reduction(min:min_y) reduction(max:max_y)
        for (int i = 1; i < n; ++i) {
            min_x = std::min(min_x, particles[i].position.x);
            max_x = std::max(max_x, particles[i].position.x);
            min_y = std::min(min_y, particles[i].position.y);
            max_y = std::max(max_y, particles[i].position.y);
        }

        // Step 2: Set up the spatial grid.
        const float cell_size = params.cullRadius;
        const int grid_width = (max_x > min_x) ? static_cast<int>(std::ceil((max_x - min_x) / cell_size)) : 1;
        const int grid_height = (max_y > min_y) ? static_cast<int>(std::ceil((max_y - min_y) / cell_size)) : 1;
        const int grid_size = grid_width * grid_height;
        
        cell_starts.assign(grid_size + 1, 0);

        // Step 3: Assign each particle to a grid cell in parallel.
        #pragma omp parallel for
        for (int i = 0; i < n; ++i) {
            int cx = static_cast<int>((particles[i].position.x - min_x) / cell_size);
            int cy = static_cast<int>((particles[i].position.y - min_y) / cell_size);
            cx = std::max(0, std::min(cx, grid_width - 1));
            cy = std::max(0, std::min(cy, grid_height - 1));
            particle_cell_map[i] = {cy * grid_width + cx, i};
        }

        // Step 4: Sort particles based on their cell index.
        std::sort(particle_cell_map.begin(), particle_cell_map.end());

        // Step 5: Create a lookup structure (cell_starts) to quickly find particles in a cell.
        int current_cell = -1;
        for (int i = 0; i < n; ++i) {
            int cell_idx = particle_cell_map[i].first;
            sorted_particle_indices[i] = particle_cell_map[i].second;
            if (cell_idx != current_cell) {
                for (int c = current_cell + 1; c <= cell_idx; ++c) {
                    cell_starts[c] = i;
                }
                current_cell = cell_idx;
            }
        }
        for (int c = current_cell + 1; c <= grid_size; ++c) {
            cell_starts[c] = n;
        }

        // Step 6: Compute forces in parallel using the grid.
        #pragma omp parallel for schedule(dynamic, 16)
        for (int i = 0; i < n; ++i) {
            const Particle& p_i = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int cx = static_cast<int>((p_i.position.x - min_x) / cell_size);
            int cy = static_cast<int>((p_i.position.y - min_y) / cell_size);
            cx = std::max(0, std::min(cx, grid_width - 1));
            cy = std::max(0, std::min(cy, grid_height - 1));

            // Iterate over the 3x3 block of neighboring cells
            for (int neighbor_cy = std::max(0, cy - 1); neighbor_cy <= std::min(grid_height - 1, cy + 1); ++neighbor_cy) {
                for (int neighbor_cx = std::max(0, cx - 1); neighbor_cx <= std::min(grid_width - 1, cx + 1); ++neighbor_cx) {
                    int neighbor_cell_idx = neighbor_cy * grid_width + neighbor_cx;
                    
                    int start_idx = cell_starts[neighbor_cell_idx];
                    int end_idx = cell_starts[neighbor_cell_idx + 1];

                    // Iterate over particles in the neighbor cell
                    for (int k = start_idx; k < end_idx; ++k) {
                        int j = sorted_particle_indices[k];
                        if (i == j) continue;
                        
                        total_force += computeForce(p_i, particles[j], params.cullRadius);
                    }
                }
            }
            newParticles[i] = updateParticle(p_i, total_force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}