#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdint>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    
    // Struct to store sort keys and mapping to original particle index
    struct SortEntry {
        uint32_t cellHash;
        int particleId;
        
        // Sort primarily by hash to group particles in the same grid cell
        // Secondarily by ID for stability
        bool operator<(const SortEntry& other) const {
            if (cellHash != other.cellHash) return cellHash < other.cellHash;
            return particleId < other.particleId;
        }
    };

    // Persistent buffers to minimize allocation overhead across steps
    std::vector<SortEntry> entries;
    std::vector<Particle> sortedParticles;
    std::vector<int> cellStart;
    std::vector<int> cellEnd;
    
    // Grid settings
    // 2^18 = 262144 cells, sufficient for 100k particles to keep load factor low
    // while fitting in cache.
    static constexpr int HASH_BITS = 18;
    static constexpr int HASH_SIZE = 1 << HASH_BITS;
    static constexpr int HASH_MASK = HASH_SIZE - 1;

    // Spatial hash function
    // Maps 2D grid coordinates to a hash bucket index
    inline uint32_t getHash(int cx, int cy) {
        // Large primes to scramble coordinates and reduce collisions
        uint32_t x = (uint32_t)cx * 73856093;
        uint32_t y = (uint32_t)cy * 19349663;
        return (x ^ y) & HASH_MASK;
    }

public:
    void init(int numParticles, StepParameters params) override {
        // Configure OpenMP threads
        numThreads = omp_get_max_threads();
        if (numThreads < 1) numThreads = 1;
        omp_set_num_threads(numThreads);

        // Pre-allocate buffers based on particle count
        if (entries.size() != (size_t)numParticles) {
            entries.resize(numParticles);
            sortedParticles.resize(numParticles);
        }
        
        if (cellStart.size() != (size_t)HASH_SIZE) {
            cellStart.resize(HASH_SIZE);
            cellEnd.resize(HASH_SIZE);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        
        int N = (int)particles.size();
        float cullRadius = params.cullRadius;
        // Avoid division by zero
        if (cullRadius < 1e-5f) cullRadius = 1e-5f;
        
        float invCellSize = 1.0f / cullRadius;
        float cullRadiusSq = cullRadius * cullRadius;

        // 1. Compute Spatial Hash for each particle (Parallel)
        // This maps each particle to a grid cell
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; i++) {
            // Discretize position to grid coordinates
            // Using std::floor handles negative coordinates correctly
            int cx = (int)std::floor(particles[i].position.x * invCellSize);
            int cy = (int)std::floor(particles[i].position.y * invCellSize);
            
            entries[i].cellHash = getHash(cx, cy);
            entries[i].particleId = i;
        }

        // 2. Sort particles based on spatial hash (Serial)
        // This groups spatially close particles together in the array.
        // Although serial, std::sort is extremely fast for 100k integers/structs (< 5ms).
        // The benefit of linear memory access in the force loop outweighs the sort cost.
        std::sort(entries.begin(), entries.end());

        // 3. Reset Grid Index (Parallel)
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < HASH_SIZE; i++) {
            cellStart[i] = -1;
        }

        // 4. Build Grid Index (Serial)
        // Scan the sorted entries to find start/end indices of each hash bucket
        for (int i = 0; i < N; i++) {
            uint32_t h = entries[i].cellHash;
            if (cellStart[h] == -1) cellStart[h] = i;
            cellEnd[h] = i + 1;
        }

        // 5. Reorder Particles into contiguous memory (Parallel)
        // This step is crucial for cache locality. Reading 'particles' is random access,
        // but the subsequent force loop will read 'sortedParticles' sequentially.
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; i++) {
            sortedParticles[i] = particles[entries[i].particleId];
        }

        // 6. Compute Forces (Parallel)
        // Using dynamic schedule to balance load, as some areas may be denser.
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < N; i++) {
            const Particle& pi = sortedParticles[i];
            Vec2 force = {0.0f, 0.0f};
            
            // Recompute grid coords for current particle
            int cx = (int)std::floor(pi.position.x * invCellSize);
            int cy = (int)std::floor(pi.position.y * invCellSize);

            // Iterate over 3x3 neighboring cells (including self)
            // Since cullRadius == cellSize, this guarantees covering all potential interactions
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    uint32_t h = getHash(cx + dx, cy + dy);
                    
                    int start = cellStart[h];
                    if (start != -1) {
                        int end = cellEnd[h];
                        
                        // Iterate over particles in the neighbor cell
                        // Since we sorted, this is a linear scan over memory -> High Cache Hits
                        for (int j = start; j < end; j++) {
                            // Skip self (valid since i and j are indices in sorted array)
                            if (i == j) continue;
                            
                            const Particle& pj = sortedParticles[j];
                            
                            // Optimization: Check squared distance before calling computeForce
                            // This avoids sqrt() inside computeForce for distant particles
                            Vec2 dir = pj.position - pi.position;
                            float distSq = dir.x * dir.x + dir.y * dir.y;
                            
                            if (distSq < cullRadiusSq) {
                                force = force + computeForce(pi, pj, cullRadius);
                            }
                        }
                    }
                }
            }

            // Update particle physics and write back to original index location
            // This implicitly scatters the results back to the correct order
            int originalIdx = entries[i].particleId;
            newParticles[originalIdx] = updateParticle(pi, force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}