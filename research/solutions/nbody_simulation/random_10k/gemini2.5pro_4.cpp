#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <limits>

class MySimulator : public Simulator {
private:
    int numThreads = 16;

    // Grid-related members, recalculated each step
    Vec2 worldMin;
    float cellSize;
    int gridWidth;
    int gridHeight;

    // Pre-allocated grid structure and buffers
    std::vector<std::vector<int>> grid;
    std::vector<Vec2> localMins;
    std::vector<Vec2> localMaxs;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        if (localMins.size() < (size_t)numThreads) {
            localMins.resize(numThreads);
            localMaxs.resize(numThreads);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        const int n = particles.size();
        if (n == 0) {
            return;
        }

        // Step 1: Determine world bounds using a parallel reduction.
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            Vec2 lmin = { std::numeric_limits<float>::max(), std::numeric_limits<float>::max() };
            Vec2 lmax = { std::numeric_limits<float>::lowest(), std::numeric_limits<float>::lowest() };
            
            #pragma omp for nowait
            for (int i = 0; i < n; ++i) {
                lmin.x = std::min(lmin.x, particles[i].position.x);
                lmin.y = std::min(lmin.y, particles[i].position.y);
                lmax.x = std::max(lmax.x, particles[i].position.x);
                lmax.y = std::max(lmax.y, particles[i].position.y);
            }
            localMins[tid] = lmin;
            localMaxs[tid] = lmax;
        }

        Vec2 globalMin = localMins[0];
        Vec2 globalMax = localMaxs[0];
        for(int i = 1; i < numThreads; ++i) {
            globalMin.x = std::min(globalMin.x, localMins[i].x);
            globalMin.y = std::min(globalMin.y, localMins[i].y);
            globalMax.x = std::max(globalMax.x, localMaxs[i].x);
            globalMax.y = std::max(globalMax.y, localMaxs[i].y);
        }
        
        worldMin = globalMin;
        Vec2 worldMax = globalMax;

        // Add a small buffer to prevent particles from falling outside the grid.
        worldMin.x -= 0.1f;
        worldMin.y -= 0.1f;
        worldMax.x += 0.1f;
        worldMax.y += 0.1f;
        
        // Step 2: Setup grid based on world bounds and cull radius.
        cellSize = params.cullRadius;
        gridWidth = static_cast<int>((worldMax.x - worldMin.x) / cellSize) + 1;
        gridHeight = static_cast<int>((worldMax.y - worldMin.y) / cellSize) + 1;
        int numCells = gridWidth * gridHeight;

        // Reuse grid memory across steps.
        if (grid.size() < (size_t)numCells) {
            grid.resize(numCells);
        }
        for (int i = 0; i < numCells; ++i) {
            grid[i].clear();
        }
        
        // Step 3: Populate grid with particle indices. This is sequential but fast.
        for (int i = 0; i < n; ++i) {
            int cx = static_cast<int>((particles[i].position.x - worldMin.x) / cellSize);
            int cy = static_cast<int>((particles[i].position.y - worldMin.y) / cellSize);
            cx = std::max(0, std::min(cx, gridWidth - 1));
            cy = std::max(0, std::min(cy, gridHeight - 1));
            grid[cx + cy * gridWidth].push_back(i);
        }
        
        // Step 4: Compute forces and update particles in parallel.
        #pragma omp parallel for schedule(dynamic, 16)
        for (int i = 0; i < n; ++i) {
            Vec2 totalForce = {0.0f, 0.0f};
            
            // Find the cell for the current particle.
            int cx = static_cast<int>((particles[i].position.x - worldMin.x) / cellSize);
            int cy = static_cast<int>((particles[i].position.y - worldMin.y) / cellSize);
            cx = std::max(0, std::min(cx, gridWidth - 1));
            cy = std::max(0, std::min(cy, gridHeight - 1));
            
            // Iterate over the 3x3 block of cells around the particle's cell.
            for (int dx = -1; dx <= 1; ++dx) {
                for (int dy = -1; dy <= 1; ++dy) {
                    int neighbor_cx = cx + dx;
                    int neighbor_cy = cy + dy;
                    
                    if (neighbor_cx >= 0 && neighbor_cx < gridWidth &&
                        neighbor_cy >= 0 && neighbor_cy < gridHeight) {
                        
                        int cellIndex = neighbor_cx + neighbor_cy * gridWidth;
                        for (int j_idx : grid[cellIndex]) {
                            if (i == j_idx) continue;
                            totalForce += computeForce(particles[i], particles[j_idx], params.cullRadius);
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(particles[i], totalForce, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}