// Baseline for N-body simulation - simple OpenMP parallel brute-force
// O(N²) approach with parallel outer loop
// Solutions should aim to beat this baseline

#include "world.h"
#include <omp.h>

class BaselineSimulator : public Simulator {
private:
    int numThreads = 16;
    
public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
    }
    
    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        #pragma omp parallel for schedule(dynamic, 16)
        for (int i = 0; i < (int)particles.size(); i++) {
            auto pi = particles[i];
            Vec2 force = Vec2(0.0f, 0.0f);
            
            for (size_t j = 0; j < particles.size(); j++) {
                if (j == (size_t)i) continue;
                if ((pi.position - particles[j].position).length() < params.cullRadius) {
                    force += computeForce(pi, particles[j], params.cullRadius);
                }
            }
            
            newParticles[i] = updateParticle(pi, force, params.deltaTime);
        }
    }
};

Simulator* createBaselineSimulator() {
    return new BaselineSimulator();
}
