#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

class MySimulator : public Simulator {
private:
    // Using 16 threads for the 16 vCPUs of the c7i.4xlarge instance.
    static constexpr int NUM_THREADS = 16;
    // World size as specified in evaluation details. Assumes a square world from [0, worldSize].
    static constexpr float WORLD_SIZE = 100.0f;
    // A finer grid gives better performance by reducing unnecessary pair checks.
    // cell size = cullRadius / this divisor. 4.0f is a good trade-off.
    static constexpr float CELL_SIZE_DIVISOR = 4.0f;

    // Grid data structures, initialized in init() and reused in each simulateStep().
    float cellSize;
    float invCellSize;
    int gridDimX;
    int gridDimY;

    // Per-particle, stores the 1D index of the grid cell it belongs to.
    std::vector<int> particleCellIndices;
    // An array of particle indices [0, 1, ..., N-1] that will be sorted
    // based on cell index.
    std::vector<int> sortedParticleIds;
    // For each cell, stores the starting index in sortedParticleIds.
    // The end index is the start index of the next cell.
    std::vector<int> cellStartIndices;

public:
    MySimulator() = default;
    ~MySimulator() override = default;

    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(NUM_THREADS);

        cellSize = params.cullRadius / CELL_SIZE_DIVISOR;
        invCellSize = 1.0f / cellSize;
        gridDimX = static_cast<int>(std::ceil(WORLD_SIZE / cellSize));
        gridDimY = static_cast<int>(std::ceil(WORLD_SIZE / cellSize));
        
        // Pre-allocate memory for our data structures to avoid reallocations.
        particleCellIndices.resize(numParticles);
        sortedParticleIds.resize(numParticles);
        cellStartIndices.resize(gridDimX * gridDimY + 1);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        const int numParticles = static_cast<int>(particles.size());
        if (numParticles == 0) return;

        const int numCells = gridDimX * gridDimY;

        // Step 1: Assign particles to grid cells. This is a data-parallel operation.
        #pragma omp parallel for
        for (int i = 0; i < numParticles; ++i) {
            const auto& p = particles[i];
            
            // Calculate 2D grid cell coordinates.
            int cellX = static_cast<int>(p.position.x * invCellSize);
            int cellY = static_cast<int>(p.position.y * invCellSize);
            
            // Clamp coordinates to be within grid bounds.
            cellX = std::max(0, std::min(gridDimX - 1, cellX));
            cellY = std::max(0, std::min(gridDimY - 1, cellY));
            
            // Store the 1D cell index.
            particleCellIndices[i] = cellX + cellY * gridDimX;
            sortedParticleIds[i] = i;
        }

        // Step 2: Sort particle IDs based on their cell index.
        // This brings particles in the same cell together in the sortedParticleIds array.
        // std::sort is sequential but very fast for N=10000.
        std::sort(sortedParticleIds.begin(), sortedParticleIds.end(),
                  [&](int a, int b) {
                      return particleCellIndices[a] < particleCellIndices[b];
                  });

        // Step 3: Find the start index for each cell in the sorted list.
        // This allows quick access to all particles in a cell.
        // This is a sequential scan, but it's O(N + numCells), which is fast.
        std::fill(cellStartIndices.begin(), cellStartIndices.end(), numParticles);
        cellStartIndices[numCells] = numParticles; // Sentinel for the last cell.
        int lastCellIdx = -1;
        for (int i = 0; i < numParticles; ++i) {
            int p_id = sortedParticleIds[i];
            int cellIdx = particleCellIndices[p_id];
            if (cellIdx > lastCellIdx) {
                for (int c = lastCellIdx + 1; c <= cellIdx; ++c) {
                    cellStartIndices[c] = i;
                }
                lastCellIdx = cellIdx;
            }
        }
        
        // Step 4: Compute forces in parallel using the grid.
        #pragma omp parallel for schedule(dynamic, 16)
        for (int i = 0; i < numParticles; ++i) {
            const Particle& pi = particles[i];
            Vec2 totalForce = {0.0f, 0.0f};

            const int cellIdx = particleCellIndices[i];
            const int cellY = cellIdx / gridDimX;
            const int cellX = cellIdx % gridDimX;
            
            // Determine the search area around the particle's cell.
            // This needs to be large enough to cover the cullRadius.
            const int searchRadius = static_cast<int>(std::ceil(params.cullRadius * invCellSize));

            // Iterate over the neighboring cells.
            for (int ny = cellY - searchRadius; ny <= cellY + searchRadius; ++ny) {
                for (int nx = cellX - searchRadius; nx <= cellX + searchRadius; ++nx) {
                    // Check if the neighbor cell is within grid bounds.
                    if (nx >= 0 && nx < gridDimX && ny >= 0 && ny < gridDimY) {
                        int neighborCellIdx = nx + ny * gridDimX;
                        int start = cellStartIndices[neighborCellIdx];
                        int end = cellStartIndices[neighborCellIdx + 1];

                        // Iterate over particles in the neighbor cell.
                        for (int k = start; k < end; ++k) {
                            int j = sortedParticleIds[k];
                            // A particle does not exert force on itself.
                            if (i == j) continue;
                            const Particle& pj = particles[j];
                            totalForce += computeForce(pi, pj, params.cullRadius);
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(pi, totalForce, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}