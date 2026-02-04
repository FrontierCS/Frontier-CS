#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>

class MySimulator : public Simulator {
private:
    int numThreads;
    
    // Buffers for grid-based spatial partitioning
    // We sort particles into a grid to improve cache locality and pruning
    std::vector<Particle> sortedParticles;
    std::vector<int> gridCounts;
    std::vector<int> gridStarts;
    // Per-thread histograms for parallel sorting
    std::vector<std::vector<int>> threadCounts; 

public:
    MySimulator() : numThreads(1) {}

    void init(int numParticles, StepParameters params) override {
        numThreads = omp_get_max_threads();
        // Use all available threads
        if (numThreads < 1) numThreads = 1;
        omp_set_num_threads(numThreads);
        
        // Pre-allocate buffers to avoid reallocation during simulation
        sortedParticles.resize(numParticles);
        threadCounts.resize(numThreads);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        int N = (int)particles.size();
        if (N == 0) return;
        
        // Ensure output vector is correctly sized
        if (newParticles.size() != particles.size()) {
            newParticles.resize(particles.size());
        }

        // 1. Calculate Bounding Box of the world dynamically
        float minX = std::numeric_limits<float>::max();
        float maxX = std::numeric_limits<float>::lowest();
        float minY = std::numeric_limits<float>::max();
        float maxY = std::numeric_limits<float>::lowest();

        #pragma omp parallel reduction(min:minX, minY) reduction(max:maxX, maxY)
        for (int i = 0; i < N; i++) {
            Vec2 p = particles[i].position;
            if (p.x < minX) minX = p.x;
            if (p.x > maxX) maxX = p.x;
            if (p.y < minY) minY = p.y;
            if (p.y > maxY) maxY = p.y;
        }
        
        // Add small epsilon to bounds to handle edge cases
        minX -= 0.1f; minY -= 0.1f;
        maxX += 0.1f; maxY += 0.1f;
        
        float width = maxX - minX;
        float height = maxY - minY;
        
        // 2. Setup Grid
        // A cell size of ~2.0 provides a good balance between culling efficiency 
        // and grid traversal overhead for a cullRadius of 25.0 in a 100.0 world.
        // Smaller cells (e.g. 2.0) cull better than larger cells (e.g. 25.0).
        float targetCellSize = 2.0f;
        int dimX = std::max(1, (int)(width / targetCellSize));
        int dimY = std::max(1, (int)(height / targetCellSize));
        
        float cellSizeX = width / dimX;
        float cellSizeY = height / dimY;
        
        int numCells = dimX * dimY;
        
        // Resize grid buffers if the grid dimensions changed
        if ((int)gridCounts.size() != numCells) {
            gridCounts.resize(numCells);
            gridStarts.resize(numCells);
        }
        
        // 3. Parallel Sort / Binning
        // We use a parallel counting sort approach to organize particles by cell.
        
        // Step 3a: Compute per-thread histograms
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            if ((int)threadCounts[tid].size() != numCells) {
                threadCounts[tid].resize(numCells);
            }
            // Clear counts
            std::fill(threadCounts[tid].begin(), threadCounts[tid].end(), 0);
            
            #pragma omp for
            for (int i = 0; i < N; i++) {
                const Vec2& p = particles[i].position;
                int cx = (int)((p.x - minX) / cellSizeX);
                int cy = (int)((p.y - minY) / cellSizeY);
                // Clamp indices
                if (cx >= dimX) cx = dimX - 1; else if (cx < 0) cx = 0;
                if (cy >= dimY) cy = dimY - 1; else if (cy < 0) cy = 0;
                
                int cellIdx = cy * dimX + cx;
                threadCounts[tid][cellIdx]++;
            }
        }
        
        // Step 3b: Compute global offsets (Prefix Sum)
        // Convert threadCounts to local offsets and aggregate into gridCounts
        #pragma omp parallel for
        for (int c = 0; c < numCells; c++) {
            int sum = 0;
            for (int t = 0; t < numThreads; t++) {
                int count = threadCounts[t][c];
                threadCounts[t][c] = sum; // Store offset for this thread
                sum += count;
            }
            gridCounts[c] = sum;
        }
        
        // Compute start indices for each cell in the sorted array
        int current = 0;
        for (int c = 0; c < numCells; c++) {
            gridStarts[c] = current;
            current += gridCounts[c];
        }
        
        // Step 3c: Scatter particles to sorted array
        // Each thread writes its particles to the correct pre-calculated positions
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            int tid = omp_get_thread_num();
            const Vec2& p = particles[i].position;
            int cx = (int)((p.x - minX) / cellSizeX);
            int cy = (int)((p.y - minY) / cellSizeY);
            if (cx >= dimX) cx = dimX - 1; else if (cx < 0) cx = 0;
            if (cy >= dimY) cy = dimY - 1; else if (cy < 0) cy = 0;
            
            int cellIdx = cy * dimX + cx;
            
            // Get unique position for this particle
            int localOff = threadCounts[tid][cellIdx]++;
            int globalPos = gridStarts[cellIdx] + localOff;
            
            sortedParticles[globalPos] = particles[i];
        }

        // 4. Force Calculation
        float cullR = params.cullRadius;
        float cullRSq = cullR * cullR;
        float dt = params.deltaTime;
        
        // Determine search range in grid cells
        int searchRadX = (int)(cullR / cellSizeX) + 1;
        int searchRadY = (int)(cullR / cellSizeY) + 1;

        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < N; i++) {
            const Particle& pi = particles[i];
            Vec2 pos = pi.position;
            Vec2 force{0.0f, 0.0f};
            
            int cx = (int)((pos.x - minX) / cellSizeX);
            int cy = (int)((pos.y - minY) / cellSizeY);
            if (cx >= dimX) cx = dimX - 1; else if (cx < 0) cx = 0;
            if (cy >= dimY) cy = dimY - 1; else if (cy < 0) cy = 0;
            
            int minGX = std::max(0, cx - searchRadX);
            int maxGX = std::min(dimX - 1, cx + searchRadX);
            int minGY = std::max(0, cy - searchRadY);
            int maxGY = std::min(dimY - 1, cy + searchRadY);
            
            for (int gy = minGY; gy <= maxGY; gy++) {
                int rowOffset = gy * dimX;
                for (int gx = minGX; gx <= maxGX; gx++) {
                    int gIdx = rowOffset + gx;
                    int start = gridStarts[gIdx];
                    int count = gridCounts[gIdx];
                    
                    if (count == 0) continue;
                    
                    int end = start + count;
                    for (int j = start; j < end; j++) {
                        const Particle& pj = sortedParticles[j];
                        
                        // Avoid self-interaction
                        if (pi.id == pj.id) continue;
                        
                        float dx = pj.position.x - pos.x;
                        float dy = pj.position.y - pos.y;
                        
                        // Fast bounding box rejection to avoid sqrt
                        if (dx > cullR || dx < -cullR) continue;
                        if (dy > cullR || dy < -cullR) continue;
                        
                        float d2 = dx*dx + dy*dy;
                        if (d2 <= cullRSq) {
                            force += computeForce(pi, pj, cullR);
                        }
                    }
                }
            }
            newParticles[i] = updateParticle(pi, force, dt);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}