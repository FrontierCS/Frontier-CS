#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <utility>

class MySimulator : public Simulator {
private:
    int num_threads_;
    std::vector<std::pair<int, int>> particle_cells_;
    std::vector<int> cell_starts_;

public:
    void init(int numParticles, StepParameters params) override {
        num_threads_ = omp_get_max_threads();
        omp_set_num_threads(num_threads_);

        if (particle_cells_.size() < (size_t)numParticles) {
            particle_cells_.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = particles.size();
        if (n == 0) {
            return;
        }

        const float cullRadius = params.cullRadius;

        // Step 1: Compute bounding box of particles
        float min_x = particles[0].position.x, max_x = particles[0].position.x;
        float min_y = particles[0].position.y, max_y = particles[0].position.y;

        #pragma omp parallel for reduction(min:min_x, min_y) reduction(max:max_x, max_y)
        for (int i = 1; i < n; ++i) {
            min_x = std::min(min_x, particles[i].position.x);
            min_y = std::min(min_y, particles[i].position.y);
            max_x = std::max(max_x, particles[i].position.x);
            max_y = std::max(max_y, particles[i].position.y);
        }
        
        // Add a small buffer to handle particles near the edge
        const float buffer = 1.0f;
        min_x -= buffer;
        min_y -= buffer;
        max_x += buffer;
        max_y += buffer;

        // Step 2: Setup grid
        const float cell_size = cullRadius;
        const int grid_dim_x = static_cast<int>((max_x - min_x) / cell_size) + 1;
        const int grid_dim_y = static_cast<int>((max_y - min_y) / cell_size) + 1;
        const int num_cells = grid_dim_x * grid_dim_y;

        // Step 3: Assign particles to cells
        #pragma omp parallel for
        for (int i = 0; i < n; ++i) {
            int ix = static_cast<int>((particles[i].position.x - min_x) / cell_size);
            int iy = static_cast<int>((particles[i].position.y - min_y) / cell_size);
            
            ix = std::max(0, std::min(grid_dim_x - 1, ix));
            iy = std::max(0, std::min(grid_dim_y - 1, iy));

            particle_cells_[i] = {iy * grid_dim_x + ix, i};
        }

        // Step 4: Sort particles by cell index.
        std::sort(particle_cells_.begin(), particle_cells_.begin() + n);

        // Step 5: Build cell start indices (sequentially)
        if (cell_starts_.size() < (size_t)(num_cells + 1)) {
            cell_starts_.resize(num_cells + 1);
        }
        
        cell_starts_.assign(num_cells + 1, n);

        if (n > 0) {
            cell_starts_[particle_cells_[0].first] = 0;
            for (int i = 1; i < n; i++) {
                if (particle_cells_[i].first > particle_cells_[i-1].first) {
                    cell_starts_[particle_cells_[i].first] = i;
                }
            }

            for (int c = num_cells - 1; c >= 0; c--) {
                if (cell_starts_[c] == n) {
                    cell_starts_[c] = cell_starts_[c + 1];
                }
            }
        } else {
            std::fill(cell_starts_.begin(), cell_starts_.begin() + num_cells + 1, 0);
        }

        // Step 6: Compute forces using the grid
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < n; ++i) {
            const Particle& p_i = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int ix = static_cast<int>((p_i.position.x - min_x) / cell_size);
            int iy = static_cast<int>((p_i.position.y - min_y) / cell_size);
            
            ix = std::max(0, std::min(grid_dim_x - 1, ix));
            iy = std::max(0, std::min(grid_dim_y - 1, iy));

            for (int neighbor_iy = iy - 1; neighbor_iy <= iy + 1; ++neighbor_iy) {
                for (int neighbor_ix = ix - 1; neighbor_ix <= ix + 1; ++neighbor_ix) {
                    if (neighbor_ix >= 0 && neighbor_ix < grid_dim_x &&
                        neighbor_iy >= 0 && neighbor_iy < grid_dim_y) {
                        
                        int cell_hash = neighbor_iy * grid_dim_x + neighbor_ix;
                        int start_idx = cell_starts_[cell_hash];
                        int end_idx = cell_starts_[cell_hash + 1];

                        for (int k = start_idx; k < end_idx; ++k) {
                            int j_idx = particle_cells_[k].second;
                            if (i == j_idx) continue;
                            
                            total_force += computeForce(p_i, particles[j_idx], cullRadius);
                        }
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