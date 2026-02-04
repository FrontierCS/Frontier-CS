#include "world.h"
#include <omp.h>
#include <vector>
#include <atomic>
#include <cmath>
#include <algorithm>
#include <memory>

class SpatialHashSimulator : public Simulator {
private:
    // Hash table configuration
    // 262144 (2^18) buckets to minimize collisions for 100k particles
    static const int HASH_SIZE = 262144;
    static const int HASH_MASK = HASH_SIZE - 1;

    // Persistent storage for grid
    // heads: array of atomic integers pointing to the first particle in a bucket
    // nexts: array of integers for the linked list of particles
    std::atomic<int>* heads;
    std::vector<int> nexts;
    int numThreads;

    // Spatial hash function
    inline int getHash(int x, int y) const {
        // Large primes to minimize collisions in the hash table
        unsigned int ux = (unsigned int)x * 73856093;
        unsigned int uy = (unsigned int)y * 19349663;
        return (int)((ux ^ uy) & HASH_MASK);
    }

    // Helper to calculate grid coordinate
    inline int fastFloor(float x) const {
        return (int)std::floor(x);
    }

public:
    SpatialHashSimulator() : heads(nullptr), numThreads(1) {
        // Allocate array of atomics
        heads = new std::atomic<int>[HASH_SIZE];
    }

    ~SpatialHashSimulator() {
        delete[] heads;
    }

    void init(int numParticles, StepParameters params) override {
        // Configure threads
        numThreads = omp_get_max_threads();
        if (numThreads < 1) numThreads = 1;
        omp_set_num_threads(numThreads);

        // Pre-allocate linked list buffer
        if ((int)nexts.size() != numParticles) {
            nexts.resize(numParticles);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = (int)particles.size();
        const float r = params.cullRadius;
        const float rSq = r * r;
        const float invR = 1.0f / r;

        // 1. Clear Grid Headers (Parallel)
        #pragma omp parallel for
        for (int i = 0; i < HASH_SIZE; i++) {
            heads[i].store(-1, std::memory_order_relaxed);
        }

        // 2. Build Grid (Parallel)
        // Insert particles into the spatial hash table
        #pragma omp parallel for
        for (int i = 0; i < n; i++) {
            int cx = fastFloor(particles[i].position.x * invR);
            int cy = fastFloor(particles[i].position.y * invR);
            int h = getHash(cx, cy);

            // Atomic insertion at the head of the list
            // memory_order_relaxed is safe here because of the implicit barrier 
            // at the end of the parallel region before the next phase.
            nexts[i] = heads[h].exchange(i, std::memory_order_relaxed);
        }

        // 3. Compute Forces and Update (Parallel)
        // Use dynamic scheduling to handle load imbalance due to particle clustering
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < n; i++) {
            Vec2 pos = particles[i].position;
            int cx = fastFloor(pos.x * invR);
            int cy = fastFloor(pos.y * invR);
            
            Vec2 totalForce = {0.0f, 0.0f};

            // Check the 3x3 block of cells around the particle
            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    int h = getHash(cx + dx, cy + dy);
                    
                    // Traverse the linked list for this bucket
                    int j = heads[h].load(std::memory_order_relaxed);
                    while (j != -1) {
                        if (i != j) {
                            Vec2 d = particles[j].position - pos;
                            
                            // Check squared distance to filter particles
                            // This avoids the sqrt call in computeForce for particles
                            // that are in the neighbor cells but outside the radius.
                            float distSq = d.x*d.x + d.y*d.y;
                            if (distSq <= rSq) {
                                totalForce += computeForce(particles[i], particles[j], r);
                            }
                        }
                        j = nexts[j];
                    }
                }
            }

            // Integrate and store result
            newParticles[i] = updateParticle(particles[i], totalForce, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new SpatialHashSimulator();
}