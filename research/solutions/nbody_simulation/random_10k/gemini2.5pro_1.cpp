#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <utility>

class MySimulator : public Simulator {
private:
    int numThreads;

    // Grid properties
    Vec2 min_coord;
    float cell_size;
    int grid_dim_x;
    int grid_dim_y;

    // Grid data structures in CSR-like format
    std::vector<int> cell_particle_indices;
    std::vector<int> cell_starts;

    // A temporary buffer used for building the grid to avoid reallocations
    std::vector<std::pair<int, int>> particle_cell_pairs;

public:
    void init(int numParticles, StepParameters params) override {
        // Use all available vCPUs on the c7i.4xlarge instance
        numThreads = 16;
        omp_set_num_threads(numThreads);

        // Pre-allocate memory to avoid reallocations during simulation steps
        if (particle_cell_pairs.capacity() < (size_t)numParticles) {
            particle_cell_pairs.reserve(numParticles);
        }
        if (cell_particle_indices.capacity() < (size_t)numParticles) {
            cell_particle_indices.reserve(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const size_t n = particles.size();
        if (n == 0) return;

        // 1. Determine the bounding box of all particles in parallel
        Vec2 global_min_p = { FLT_MAX, FLT_MAX };
        Vec2 global_max_p = { -FLT_MAX, -FLT_MAX };

        #pragma omp parallel
        {
            Vec2 local_min_p = { FLT_MAX, FLT_MAX };
            Vec2 local_max_p = { -FLT_MAX, -FLT_MAX };

            #pragma omp for nowait
            for (size_t i = 0; i < n; ++i) {
                const auto& pos = particles[i].position;
                local_min_p.x = std::min(local_min_p.x, pos.x);
                local_min_p.y = std::min(local_min_p.y, pos.y);
                local_max_p.x = std::max(local_max_p.x, pos.x);
                local_max_p.y = std::max(local_max_p.y, pos.y);
            }

            #pragma omp critical
            {
                global_min_p.x = std::min(global_min_p.x, local_min_p.x);
                global_min_p.y = std::min(global_min_p.y, local_min_p.y);
                global_max_p.x = std::max(global_max_p.x, local_max_p.x);
                global_max_p.y = std::max(global_max_p.y, local_max_p.y);
            }
        }
        
        min_coord = global_min_p;
        cell_size = params.cullRadius;
        if (cell_size <= 1e-5f) cell_size = 1.0f;
        
        grid_dim_x = static_cast<int>((global_max_p.x - min_coord.x) / cell_size) + 1;
        grid_dim_y = static_cast<int>((global_max_p.y - min_coord.y) / cell_size) + 1;
        const int num_cells = grid_dim_x * grid_dim_y;

        // 2. Build the spatial grid
        // Assign each particle to a cell
        particle_cell_pairs.resize(n);
        #pragma omp parallel for
        for (size_t i = 0; i < n; ++i) {
            const auto& p_pos = particles[i].position;
            int cx = static_cast<int>((p_pos.x - min_coord.x) / cell_size);
            int cy = static_cast<int>((p_pos.y - min_coord.y) / cell_size);
            
            // Clamp coordinates to be within grid bounds to handle floating point edge cases
            cx = std::max(0, std::min(cx, grid_dim_x - 1));
            cy = std::max(0, std::min(cy, grid_dim_y - 1));

            particle_cell_pairs[i] = {cy * grid_dim_x + cx, static_cast<int>(i)};
        }

        // Sort particles by their cell index. This groups particles in the same cell together.
        std::sort(particle_cell_pairs.begin(), particle_cell_pairs.end());

        // Create the CSR-like representation of the grid
        cell_particle_indices.resize(n);
        cell_starts.assign(num_cells + 1, 0);

        #pragma omp parallel for
        for (size_t i = 0; i < n; ++i) {
            cell_particle_indices[i] = particle_cell_pairs[i].second;
        }

        // This serial part builds the 'starts' array. It's O(N + num_cells), which is very fast.
        if (n > 0) {
            int last_cell_id = -1;
            for (size_t i = 0; i < n; ++i) {
                int current_cell_id = particle_cell_pairs[i].first;
                if (current_cell_id > last_cell_id) {
                    for (int c = last_cell_id + 1; c <= current_cell_id; ++c) {
                        cell_starts[c] = i;
                    }
                    last_cell_id = current_cell_id;
                }
            }
            for (int c = last_cell_id + 1; c <= num_cells; ++c) {
                cell_starts[c] = n;
            }
        }

        // 3. Compute forces in parallel using the grid for neighbor finding
        #pragma omp parallel for schedule(dynamic, 16)
        for (size_t i = 0; i < n; ++i) {
            const auto& pi = particles[i];
            Vec2 force = {0.0f, 0.0f};

            const auto& p_pos = pi.position;
            int cx = static_cast<int>((p_pos.x - min_coord.x) / cell_size);
            int cy = static_cast<int>((p_pos.y - min_coord.y) / cell_size);

            // Iterate over the 3x3 block of cells around the particle's cell
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int neighbor_cx = cx + dx;
                    int neighbor_cy = cy + dy;

                    // Check if the neighboring cell is within the grid bounds
                    if (neighbor_cx >= 0 && neighbor_cx < grid_dim_x &&
                        neighbor_cy >= 0 && neighbor_cy < grid_dim_y) {
                        
                        int cell_idx = neighbor_cy * grid_dim_x + neighbor_cx;
                        int start_idx = cell_starts[cell_idx];
                        int end_idx = cell_starts[cell_idx + 1];

                        // Iterate over particles in the neighboring cell
                        for (int k = start_idx; k < end_idx; ++k) {
                            int j = cell_particle_indices[k];
                            if (static_cast<size_t>(j) == i) continue;
                            
                            // Check distance and compute force, matching baseline logic for correctness
                            if ((pi.position - particles[j].position).length() < params.cullRadius) {
                                force += computeForce(pi, particles[j], params.cullRadius);
                            }
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(pi, force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}