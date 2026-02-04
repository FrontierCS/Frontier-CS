#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    std::vector<std::pair<int, int>> particle_cell_pairs;
    std::vector<int> cell_starts;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        if (particle_cell_pairs.size() != (size_t)numParticles) {
            particle_cell_pairs.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = particles.size();
        if (n == 0) {
            return;
        }

        float min_x = std::numeric_limits<float>::max();
        float max_x = std::numeric_limits<float>::lowest();
        float min_y = std::numeric_limits<float>::max();
        float max_y = std::numeric_limits<float>::lowest();

        #pragma omp parallel for reduction(min:min_x, min_y) reduction(max:max_x, max_y)
        for (int i = 0; i < n; ++i) {
            min_x = std::min(min_x, particles[i].position.x);
            max_x = std::max(max_x, particles[i].position.x);
            min_y = std::min(min_y, particles[i].position.y);
            max_y = std::max(max_y, particles[i].position.y);
        }

        const float cell_size = params.cullRadius;
        const float domain_width = max_x - min_x;
        const float domain_height = max_y - min_y;

        const int grid_cols = std::max(1, static_cast<int>(std::ceil(domain_width / cell_size)));
        const int grid_rows = std::max(1, static_cast<int>(std::ceil(domain_height / cell_size)));
        const int num_cells = grid_cols * grid_rows;

        #pragma omp parallel for
        for (int i = 0; i < n; ++i) {
            const auto& p = particles[i];
            int cell_x = static_cast<int>((p.position.x - min_x) / cell_size);
            int cell_y = static_cast<int>((p.position.y - min_y) / cell_size);
            
            cell_x = std::max(0, std::min(grid_cols - 1, cell_x));
            cell_y = std::max(0, std::min(grid_rows - 1, cell_y));
            
            int cell_idx = cell_y * grid_cols + cell_x;
            particle_cell_pairs[i] = {cell_idx, i};
        }

        std::sort(particle_cell_pairs.begin(), particle_cell_pairs.end());

        if (cell_starts.size() < (size_t)num_cells + 1) {
            cell_starts.resize(num_cells + 1);
        }
        
        cell_starts[0] = 0;
        int last_cell_idx = -1;
        if (n > 0) {
            last_cell_idx = particle_cell_pairs[0].first;
            for(int c = 0; c <= last_cell_idx; ++c) {
                cell_starts[c] = 0;
            }
        }
        for (int i = 1; i < n; ++i) {
            int current_cell_idx = particle_cell_pairs[i].first;
            if (current_cell_idx != last_cell_idx) {
                for(int c = last_cell_idx + 1; c <= current_cell_idx; ++c) {
                    cell_starts[c] = i;
                }
                last_cell_idx = current_cell_idx;
            }
        }
        for (int c = last_cell_idx + 1; c <= num_cells; ++c) {
            cell_starts[c] = n;
        }

        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < n; ++i) {
            const auto& pi = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int cell_x = static_cast<int>((pi.position.x - min_x) / cell_size);
            int cell_y = static_cast<int>((pi.position.y - min_y) / cell_size);
            cell_x = std::max(0, std::min(grid_cols - 1, cell_x));
            cell_y = std::max(0, std::min(grid_rows - 1, cell_y));

            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int neighbor_cx = cell_x + dx;
                    int neighbor_cy = cell_y + dy;

                    if (neighbor_cx >= 0 && neighbor_cx < grid_cols &&
                        neighbor_cy >= 0 && neighbor_cy < grid_rows)
                    {
                        int neighbor_cell_idx = neighbor_cy * grid_cols + neighbor_cx;
                        int start_idx = cell_starts[neighbor_cell_idx];
                        int end_idx = cell_starts[neighbor_cell_idx + 1];

                        for (int k = start_idx; k < end_idx; ++k) {
                            int j = particle_cell_pairs[k].second;
                            if (i == j) continue;
                            total_force += computeForce(pi, particles[j], params.cullRadius);
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