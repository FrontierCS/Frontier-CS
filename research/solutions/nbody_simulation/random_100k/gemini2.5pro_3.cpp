#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cfloat>
#include <atomic>

class MySimulator : public Simulator {
private:
    int numThreads;

    // Buffers reused across steps to avoid reallocation
    std::vector<int> particle_cell_ids;
    std::vector<int> cell_starts;
    std::vector<int> particle_indices_in_cells;
    
    // Raw pointer for atomic counters as std::vector<std::atomic> is problematic
    std::atomic<int>* atomic_cell_counters = nullptr;
    size_t atomic_counters_capacity = 0;

public:
    MySimulator() {
        // AWS c7i.4xlarge has 16 vCPUs. Using all of them provides good performance.
        numThreads = 16;
    }

    ~MySimulator() override {
        delete[] atomic_cell_counters;
    }

    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        
        // Pre-allocate buffers to the number of particles.
        if (particle_cell_ids.size() < (size_t)numParticles) {
            particle_cell_ids.resize(numParticles);
            particle_indices_in_cells.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        const int numParticles = particles.size();
        if (numParticles == 0) return;

        // 1. Determine bounding box of particles in parallel
        float min_x = FLT_MAX, min_y = FLT_MAX;
        float max_x = -FLT_MAX, max_y = -FLT_MAX;

        #pragma omp parallel for reduction(min:min_x, min_y) reduction(max:max_x, max_y)
        for (int i = 0; i < numParticles; ++i) {
            min_x = std::min(min_x, particles[i].position.x);
            min_y = std::min(min_y, particles[i].position.y);
            max_x = std::max(max_x, particles[i].position.x);
            max_y = std::max(max_y, particles[i].position.y);
        }
        Vec2 worldMin = {min_x, min_y};
        Vec2 worldMax = {max_x, max_y};
        
        // Add a margin to handle particles near the edge of the grid
        worldMin -= Vec2{params.cullRadius, params.cullRadius};
        worldMax += Vec2{params.cullRadius, params.cullRadius};

        // 2. Setup grid properties
        // A smaller cell size is more optimal, balancing the number of cells to check 
        // against the number of particles per cell. A value of 5.0f was found to be effective.
        const float cellSize = 5.0f; 
        int gridDimX = static_cast<int>(ceil((worldMax.x - worldMin.x) / cellSize));
        int gridDimY = static_cast<int>(ceil((worldMax.y - worldMin.y) / cellSize));
        if (gridDimX <= 0) gridDimX = 1;
        if (gridDimY <= 0) gridDimY = 1;
        const int numCells = gridDimX * gridDimY;

        // 3. Build grid in parallel
        // 3a. Count particles per cell using per-thread local histograms
        cell_starts.assign(numCells + 1, 0);
        
        #pragma omp parallel
        {
            std::vector<int> local_counts(numCells, 0);
            #pragma omp for nowait
            for (int i = 0; i < numParticles; ++i) {
                const auto& p = particles[i];
                int cx = static_cast<int>((p.position.x - worldMin.x) / cellSize);
                int cy = static_cast<int>((p.position.y - worldMin.y) / cellSize);
                cx = std::max(0, std::min(cx, gridDimX - 1));
                cy = std::max(0, std::min(cy, gridDimY - 1));
                int cellId = cx + cy * gridDimX;
                particle_cell_ids[i] = cellId;
                local_counts[cellId]++;
            }

            // Reduce local counts into the global count array (cell_starts is reused for this)
            #pragma omp critical
            {
                for (int i = 0; i < numCells; ++i) {
                    cell_starts[i + 1] += local_counts[i];
                }
            }
        }
        
        // 3b. Serial prefix sum to get cell start indices in the final sorted array
        for (int i = 0; i < numCells; ++i) {
            cell_starts[i + 1] += cell_starts[i];
        }

        // 3c. Place particle indices into sorted array using atomic counters
        if (atomic_counters_capacity < (size_t)numCells) {
             delete[] atomic_cell_counters;
             atomic_cell_counters = new std::atomic<int>[numCells];
             atomic_counters_capacity = numCells;
        }
       
        #pragma omp parallel for
        for (int i = 0; i < numCells; ++i) {
            atomic_cell_counters[i].store(0, std::memory_order_relaxed);
        }

        #pragma omp parallel for
        for (int i = 0; i < numParticles; ++i) {
            int cellId = particle_cell_ids[i];
            int local_idx = atomic_cell_counters[cellId].fetch_add(1, std::memory_order_relaxed);
            int global_idx = cell_starts[cellId] + local_idx;
            particle_indices_in_cells[global_idx] = i;
        }

        // 4. Compute forces using the grid
        const int search_radius_in_cells = static_cast<int>(ceil(params.cullRadius / cellSize));
        
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < numParticles; ++i) {
            const auto& pi = particles[i];
            Vec2 total_force = {0.0f, 0.0f};

            int cx = static_cast<int>((pi.position.x - worldMin.x) / cellSize);
            int cy = static_cast<int>((pi.position.y - worldMin.y) / cellSize);

            for (int dy = -search_radius_in_cells; dy <= search_radius_in_cells; ++dy) {
                for (int dx = -search_radius_in_cells; dx <= search_radius_in_cells; ++dx) {
                    int neighbor_cx = cx + dx;
                    int neighbor_cy = cy + dy;

                    if (neighbor_cx >= 0 && neighbor_cx < gridDimX &&
                        neighbor_cy >= 0 && neighbor_cy < gridDimY) {
                        
                        int cellId = neighbor_cx + neighbor_cy * gridDimX;
                        int start = cell_starts[cellId];
                        int end = cell_starts[cellId + 1];

                        for (int k = start; k < end; ++k) {
                            int j = particle_indices_in_cells[k];
                            if (i == j) continue;
                            const auto& pj = particles[j];
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