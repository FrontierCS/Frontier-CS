#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdint>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    
    struct ParticleRef {
        int originalIndex;
        uint32_t hash;
    };

    // Persistent buffers to minimize allocation overhead
    std::vector<ParticleRef> pRefs;
    std::vector<Particle> sortedParticles;
    std::vector<int> cellStart;
    std::vector<int> cellEnd;
    std::vector<std::vector<Vec2>> threadForces;
    
    // Grid configuration
    // Using a large power of 2 for hash map to minimize collisions while avoiding sparse matrix overhead
    static const int HASH_SIZE = 131072; // 2^17
    static const int HASH_MASK = HASH_SIZE - 1;

public:
    void init(int numParticles, StepParameters params) override {
        // Detect and set thread count
        int max_threads = omp_get_max_threads();
        numThreads = (max_threads > 0) ? max_threads : 1;
        omp_set_num_threads(numThreads);

        // Pre-allocate memory
        pRefs.resize(numParticles);
        sortedParticles.resize(numParticles);
        
        // Resize hash map arrays
        cellStart.resize(HASH_SIZE);
        cellEnd.resize(HASH_SIZE);
        
        // Allocate per-thread force accumulation buffers
        threadForces.resize(numThreads);
        for(auto& v : threadForces) {
            v.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        int N = particles.size();
        
        // Use cell size = cullRadius / 2.0 for finer granularity.
        // This requires searching a 5x5 block of cells but approximates the circular cull area better 
        // than a 3x3 block with cell size = cullRadius.
        float cellSize = params.cullRadius * 0.5f;
        float invCellSize = 1.0f / cellSize;
        float cullRadiusSq = params.cullRadius * params.cullRadius;

        // 1. Reset thread accumulation buffers
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            // Using explicit initialization to zero
            std::fill(threadForces[tid].begin(), threadForces[tid].end(), Vec2{0.0f, 0.0f});
        }

        // 2. Assign particles to grid cells (Compute Hash) and store references
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            int ix = (int)std::floor(particles[i].position.x * invCellSize);
            int iy = (int)std::floor(particles[i].position.y * invCellSize);
            // Spatial hash using large primes
            uint32_t h = ((ix * 73856093) ^ (iy * 19349663)) & HASH_MASK;
            pRefs[i] = {i, h};
        }

        // 3. Sort particles by hash to improve cache locality during force calculation
        std::sort(pRefs.begin(), pRefs.end(), [](const ParticleRef& a, const ParticleRef& b){
            return a.hash < b.hash;
        });

        // 4. Reset grid and build start/end indices
        std::fill(cellStart.begin(), cellStart.end(), -1);
        
        // Build Grid: Populate start/end indices for each bucket
        // Also permute particles into sorted order for linear memory access
        // Serial grid build is fast enough for 100k particles
        for (int i = 0; i < N; i++) {
            uint32_t h = pRefs[i].hash;
            if (cellStart[h] == -1) cellStart[h] = i;
            cellEnd[h] = i + 1;
        }

        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            sortedParticles[i] = particles[pRefs[i].originalIndex];
        }

        // 5. Parallel Force Computation
        #pragma omp parallel 
        {
            int tid = omp_get_thread_num();
            auto& myForces = threadForces[tid];

            // Dynamic schedule handles load imbalance due to clustering
            #pragma omp for schedule(dynamic, 64)
            for (int i = 0; i < N; i++) {
                const Particle& pi = sortedParticles[i];
                int original_i = pRefs[i].originalIndex;
                
                int cx = (int)std::floor(pi.position.x * invCellSize);
                int cy = (int)std::floor(pi.position.y * invCellSize);

                // Check 5x5 neighbor block (radius 2 cells covers cullRadius)
                for (int dy = -2; dy <= 2; dy++) {
                    for (int dx = -2; dx <= 2; dx++) {
                        int nx = cx + dx;
                        int ny = cy + dy;
                        uint32_t h = ((nx * 73856093) ^ (ny * 19349663)) & HASH_MASK;
                        
                        int start = cellStart[h];
                        if (start == -1) continue;
                        int end = cellEnd[h];

                        // Iterate over potential neighbors in this bucket
                        for (int j = start; j < end; j++) {
                            // Enforce uniqueness and Newton's 3rd Law:
                            // Process pair (i, j) only once. Since we check all neighbor combinations
                            // symmetrically in the grid search, 'j > i' is sufficient to process each pair once.
                            if (j <= i) continue;

                            const Particle& pj = sortedParticles[j];

                            // Verify particle is actually in the target cell to handle hash collisions
                            // and ensure we don't process "ghost" neighbors from aliased cells
                            int px = (int)std::floor(pj.position.x * invCellSize);
                            int py = (int)std::floor(pj.position.y * invCellSize);
                            if (px != nx || py != ny) continue;

                            Vec2 dir = pj.position - pi.position;
                            float d2 = dir.x*dir.x + dir.y*dir.y;
                            
                            // Optimization: Check squared distance before calling computeForce (avoids sqrt)
                            if (d2 > cullRadiusSq || d2 < 1e-6f) continue;

                            // Calculate force
                            Vec2 force = computeForce(pi, pj, params.cullRadius);
                            
                            // Apply symmetric forces to original indices
                            // force is exerted on pi by pj.
                            int original_j = pRefs[j].originalIndex;
                            
                            myForces[original_i].x += force.x;
                            myForces[original_i].y += force.y;
                            myForces[original_j].x -= force.x;
                            myForces[original_j].y -= force.y;
                        }
                    }
                }
            }
        }

        // 6. Integrate and Finalize
        // Sum forces from all thread buffers and update particles
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            Vec2 totalForce = {0.0f, 0.0f};
            for (int t = 0; t < numThreads; t++) {
                totalForce.x += threadForces[t][i].x;
                totalForce.y += threadForces[t][i].y;
            }
            newParticles[i] = updateParticle(particles[i], totalForce, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}