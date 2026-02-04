#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>

class OptimizedSimulator : public Simulator {
private:
    int numThreads = 16;
    
    // Persistent buffers to minimize allocation overhead
    std::vector<int> cellCounts;
    std::vector<int> cellOffsets;
    std::vector<Particle> sortedParticles;
    std::vector<int> origIndices;
    std::vector<int> particleCellIndices;

public:
    void init(int numParticles, StepParameters params) override {
        // Set OpenMP threads
        omp_set_num_threads(numThreads);
        
        // Pre-allocate buffers for particle data
        sortedParticles.resize(numParticles);
        origIndices.resize(numParticles);
        particleCellIndices.resize(numParticles);
        
        // Reserve space for grid (heuristic size, will resize if needed)
        cellCounts.reserve(4096);
        cellOffsets.reserve(4096);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        int n = (int)particles.size();
        if (n == 0) return;

        float r = params.cullRadius;
        float rSq = r * r;

        // 1. Compute Bounding Box
        // Initialize with first particle to avoid checking limits constants
        float minX = particles[0].position.x;
        float maxX = particles[0].position.x;
        float minY = particles[0].position.y;
        float maxY = particles[0].position.y;

        // Simple serial pass is efficient enough for 100k particles (memory bound)
        for (int i = 1; i < n; i++) {
            float px = particles[i].position.x;
            float py = particles[i].position.y;
            if (px < minX) minX = px;
            if (px > maxX) maxX = px;
            if (py < minY) minY = py;
            if (py > maxY) maxY = py;
        }

        // Add padding to bounding box
        minX -= 0.1f; minY -= 0.1f;
        maxX += 0.1f; maxY += 0.1f;

        // 2. Setup Grid Dimensions
        // Use cell size = cullRadius. This ensures we only need to check 3x3 neighbor cells.
        int gridW = (int)((maxX - minX) / r) + 1;
        int gridH = (int)((maxY - minY) / r) + 1;
        int numCells = gridW * gridH;

        // Resize grid buffers if the grid has grown
        if ((int)cellCounts.size() < numCells) {
            cellCounts.resize(numCells);
            cellOffsets.resize(numCells);
        }

        // Clear cell counts for this step
        std::fill(cellCounts.begin(), cellCounts.begin() + numCells, 0);

        // 3. Assign Particles to Cells and Count
        for (int i = 0; i < n; i++) {
            int cx = (int)((particles[i].position.x - minX) / r);
            int cy = (int)((particles[i].position.y - minY) / r);
            
            // Clamp indices to be safe
            if (cx < 0) cx = 0; else if (cx >= gridW) cx = gridW - 1;
            if (cy < 0) cy = 0; else if (cy >= gridH) cy = gridH - 1;
            
            int cellIdx = cy * gridW + cx;
            particleCellIndices[i] = cellIdx;
            cellCounts[cellIdx]++;
        }

        // 4. Compute Cell Offsets (Prefix Sum)
        int current = 0;
        for (int c = 0; c < numCells; c++) {
            cellOffsets[c] = current;
            current += cellCounts[c];
        }

        // 5. Reorder Particles (Counting Sort / spatial hashing)
        // This improves cache locality significantly during force calculation
        // Create a temporary copy of offsets to track insertion positions
        std::vector<int> currentPos(cellOffsets.begin(), cellOffsets.begin() + numCells);
        
        for (int i = 0; i < n; i++) {
            int cIdx = particleCellIndices[i];
            int dst = currentPos[cIdx]++;
            sortedParticles[dst] = particles[i];
            origIndices[dst] = i; // Store original index to write back results correctly
        }

        // 6. Parallel Force Calculation
        // Iterate over sorted particles. Threads process chunks of spatially local particles.
        #pragma omp parallel
        {
            // Thread-local cache to store neighbor cell ranges
            // This avoids recalculating neighbors for every particle in the same cell
            int cachedCellIdx = -1;
            struct Range { int start; int end; };
            Range neighborRanges[9]; // Max 9 neighbors (3x3)
            int numNeighbors = 0;

            #pragma omp for schedule(dynamic, 64)
            for (int i = 0; i < n; i++) {
                const Particle& pi = sortedParticles[i];
                
                // Determine the cell of the current particle from its position
                int cx = (int)((pi.position.x - minX) / r);
                int cy = (int)((pi.position.y - minY) / r);
                if (cx < 0) cx = 0; else if (cx >= gridW) cx = gridW - 1;
                if (cy < 0) cy = 0; else if (cy >= gridH) cy = gridH - 1;
                
                int cellIdx = cy * gridW + cx;

                // If we moved to a new cell, update the neighbor list
                if (cellIdx != cachedCellIdx) {
                    cachedCellIdx = cellIdx;
                    numNeighbors = 0;
                    
                    int min_x = std::max(0, cx - 1);
                    int max_x = std::min(gridW - 1, cx + 1);
                    int min_y = std::max(0, cy - 1);
                    int max_y = std::min(gridH - 1, cy + 1);

                    for (int ny = min_y; ny <= max_y; ny++) {
                        int rowOffset = ny * gridW;
                        for (int nx = min_x; nx <= max_x; nx++) {
                            int nIdx = rowOffset + nx;
                            int count = cellCounts[nIdx];
                            // Only add non-empty cells
                            if (count > 0) {
                                int start = cellOffsets[nIdx];
                                neighborRanges[numNeighbors++] = {start, start + count};
                            }
                        }
                    }
                }

                Vec2 force = {0.0f, 0.0f};

                // Iterate over all candidate particles in neighbor cells
                for (int k = 0; k < numNeighbors; k++) {
                    int start = neighborRanges[k].start;
                    int end = neighborRanges[k].end;
                    
                    for (int j = start; j < end; j++) {
                        // Skip self
                        if (i == j) continue;
                        
                        const Particle& pj = sortedParticles[j];
                        float dx = pj.position.x - pi.position.x;
                        float dy = pj.position.y - pi.position.y;
                        
                        // Check squared distance first to avoid sqrt in computeForce
                        float distSq = dx*dx + dy*dy;
                        if (distSq < rSq) {
                            force += computeForce(pi, pj, r);
                        }
                    }
                }

                // Update particle and write to correct location in newParticles
                newParticles[origIndices[i]] = updateParticle(pi, force, params.deltaTime);
            }
        }
    }
};

Simulator* createSimulator() {
    return new OptimizedSimulator();
}