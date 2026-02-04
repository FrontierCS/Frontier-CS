#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <utility>

class MySimulator : public Simulator {
private:
    int numThreads = 16;

    // Grid properties recalculated each step
    Vec2 world_min;
    float cell_size;
    int grid_dim_x;
    int grid_dim_y;

    // Persistent buffers to avoid reallocation
    std::vector<std::pair<int, int>> particle_cell_map;
    std::vector<int> grid_particles;
    std::vector<int> grid_cells;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        // Pre-allocate memory to avoid reallocations in simulateStep
        if (particle_cell_map.capacity() < (size_t)numParticles) {
            particle_cell_map.reserve(numParticles);
            grid_particles.reserve(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = particles.size();
        if (n == 0) return;

        // 1. Find world bounds in parallel using thread-local reduction
        world_min = {FLT_MAX, FLT_MAX};
        Vec2 world_max = {-FLT_MAX, -FLT_MAX};
        
        #pragma omp parallel
        {
            Vec2 local_min = {FLT_MAX, FLT_MAX};
            Vec2 local_max = {-FLT_MAX, -FLT_MAX};
            #pragma omp for nowait
            for (int i = 0; i < n; ++i) {
                const auto& p_pos = particles[i].position;
                local_min.x = std::min(local_min.x, p_pos.x);
                local_min.y = std::min(local_min.y, p_pos.y);
                local_max.x = std::max(local_max.x, p_pos.x);
                local_max.y = std::max(local_max.y, p_pos.y);
            }

            #pragma omp critical
            {
                world_min.x = std::min(world_min.x, local_min.x);
                world_min.y = std::min(world_min.y, local_min.y);
                world_max.x = std::max(world_max.x, local_max.x);
                world_max.y = std::max(world_max.y, local_max.y);
            }
        }

        // 2. Setup grid properties
        cell_size = params.cullRadius;
        grid_dim_x = static_cast<int>((world_max.x - world_min.x) / cell_size) + 1;
        grid_dim_y = static_cast<int>((world_max.y - world_min.y) / cell_size) + 1;
        const int num_cells = grid_dim_x * grid_dim_y;

        // 3. Bin particles into cells in parallel
        particle_cell_map.resize(n);
        #pragma omp parallel for
        for (int i = 0; i < n; ++i) {
            int cx = static_cast<int>((particles[i].position.x - world_min.x) / cell_size);
            int cy = static_cast<int>((particles[i].position.y - world_min.y) / cell_size);
            cx = std::max(0, std::min(cx, grid_dim_x - 1));
            cy = std::max(0, std::min(cy, grid_dim_y - 1));
            particle_cell_map[i] = {cy * grid_dim_x + cx, i};
        }
        
        // 4. Sort particles by cell index to group them
        std::sort(particle_cell_map.begin(), particle_cell_map.end());

        // 5. Build the grid data structure (cell start indices and sorted particle list)
        grid_particles.resize(n);
        grid_cells.assign(num_cells + 1, 0);

        int last_cell_idx = -1;
        for (int i = 0; i < n; ++i) {
            int particle_idx = particle_cell_map[i].second;
            int cell_idx = particle_cell_map[i].first;
            grid_particles[i] = particle_idx;
            
            if (cell_idx != last_cell_idx) {
                for (int c = last_cell_idx + 1; c <= cell_idx; ++c) {
                    grid_cells[c] = i;
                }
                last_cell_idx = cell_idx;
            }
        }
        for (int c = last_cell_idx + 1; c <= num_cells; ++c) {
            grid_cells[c] = n;
        }

        // 6. Compute forces in parallel using the spatial grid
        #pragma omp parallel for schedule(dynamic, 16)
        for (int i = 0; i < n; ++i) {
            const Particle& pi = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int cx = static_cast<int>((pi.position.x - world_min.x) / cell_size);
            int cy = static_cast<int>((pi.position.y - world_min.y) / cell_size);

            // Iterate over the 3x3 neighborhood of cells
            for (int ny = cy - 1; ny <= cy + 1; ++ny) {
                for (int nx = cx - 1; nx <= cx + 1; ++nx) {
                    if (nx < 0 || nx >= grid_dim_x || ny < 0 || ny >= grid_dim_y) {
                        continue;
                    }

                    int cell_idx = ny * grid_dim_x + nx;
                    int start = grid_cells[cell_idx];
                    int end = grid_cells[cell_idx + 1];

                    for (int j = start; j < end; ++j) {
                        int pj_idx = grid_particles[j];
                        if (pj_idx == i) continue;
                        
                        const Particle& pj = particles[pj_idx];
                        if ((pi.position - pj.position).length2() < params.cullRadius * params.cullRadius) {
                            total_force += computeForce(pi, pj, params.cullRadius);
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