#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>

class MySimulator : public Simulator {
private:
    // Use all available vCPUs on the c7i.4xlarge instance
    int numThreads = 16;

    // Persistent state for memory reuse across simulation steps
    std::vector<std::vector<int>> grid;
    std::vector<int> particle_to_cell_map;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        if (numParticles > 0) {
            // Pre-allocate to avoid reallocations during the simulation steps
            particle_to_cell_map.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = particles.size();
        if (N == 0) {
            return;
        }

        // 1. Determine simulation domain and grid parameters.
        // This is done dynamically each step to adapt to particle movement.
        float minX = particles[0].position.x, maxX = minX;
        float minY = particles[0].position.y, maxY = minY;

        #pragma omp parallel for reduction(min:minX, minY) reduction(max:maxX, maxY)
        for (int i = 1; i < N; ++i) {
            minX = std::min(minX, particles[i].position.x);
            maxX = std::max(maxX, particles[i].position.x);
            minY = std::min(minY, particles[i].position.y);
            maxY = std::max(maxY, particles[i].position.y);
        }
        
        // Add a small epsilon to max bounds to handle particles exactly on an edge
        // and prevent out-of-bounds cell indices due to floating point inaccuracies.
        maxX += 1e-5f;
        maxY += 1e-5f;

        const float cellSize = params.cullRadius;
        if (cellSize <= 1e-6f) return; // Avoid division by zero or very small numbers
        
        const int gridDimX = static_cast<int>((maxX - minX) / cellSize) + 1;
        const int gridDimY = static_cast<int>((maxY - minY) / cellSize) + 1;
        const int numCells = gridDimX * gridDimY;

        // 2. Populate the grid acceleration structure.
        // This part is sequential but fast enough (O(N)) compared to force calculation.
        grid.assign(numCells, std::vector<int>());
        
        // To avoid reallocation in push_back, we count items per cell first and reserve memory.
        std::vector<int> cell_counts(numCells, 0);
        for (int i = 0; i < N; ++i) {
            int cx = static_cast<int>((particles[i].position.x - minX) / cellSize);
            int cy = static_cast<int>((particles[i].position.y - minY) / cellSize);
            
            cx = std::max(0, std::min(cx, gridDimX - 1));
            cy = std::max(0, std::min(cy, gridDimY - 1));

            int cell_idx = cy * gridDimX + cx;
            particle_to_cell_map[i] = cell_idx;
            cell_counts[cell_idx]++;
        }

        for (int i = 0; i < numCells; ++i) {
            grid[i].reserve(cell_counts[i]);
        }
        
        for (int i = 0; i < N; ++i) {
            grid[particle_to_cell_map[i]].push_back(i);
        }

        // 3. Compute forces and update particles in parallel.
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < N; i++) {
            const Particle& pi = particles[i];
            Vec2 totalForce = {0.0f, 0.0f};

            const int cell_idx_orig = particle_to_cell_map[i];
            const int cx_orig = cell_idx_orig % gridDimX;
            const int cy_orig = cell_idx_orig / gridDimX;

            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int cx = cx_orig + dx;
                    int cy = cy_orig + dy;

                    if (cx >= 0 && cx < gridDimX && cy >= 0 && cy < gridDimY) {
                        int neighbor_cell_idx = cy * gridDimX + cx;
                        for (int j_idx : grid[neighbor_cell_idx]) {
                            if (i == j_idx) continue;
                            
                            // computeForce internally handles the cullRadius check
                            totalForce += computeForce(pi, particles[j_idx], params.cullRadius);
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(pi, totalForce, params.deltaTime);
        }
    }
};

// Factory function - must be implemented
Simulator* createSimulator() {
    return new MySimulator();
}