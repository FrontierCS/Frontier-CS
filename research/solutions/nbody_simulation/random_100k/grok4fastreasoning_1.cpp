#include "world.h"
#include <vector>
#include <omp.h>
#include <algorithm>
#include <cmath>

class MySimulator : public Simulator {
private:
    float cell_size;
    float world_size = 100.0f;
    int numThreads = 16;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        cell_size = params.cullRadius / 4.0f;
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        size_t N = particles.size();
        if (N == 0) return;

        float s = cell_size;
        int nx = static_cast<int>(std::ceil(world_size / s));
        int ny = nx;
        int num_buckets = nx * ny;
        std::vector<std::vector<int>> buckets(num_buckets);

        for (size_t i = 0; i < N; ++i) {
            Vec2 pos = particles[i].position;
            int ix = static_cast<int>(std::floor(pos.x / s));
            int iy = static_cast<int>(std::floor(pos.y / s));
            ix = std::max(0, std::min(nx - 1, ix));
            iy = std::max(0, std::min(ny - 1, iy));
            int idx = iy * nx + ix;
            buckets[idx].push_back(static_cast<int>(i));
        }

        int kr = static_cast<int>(std::ceil(params.cullRadius / s));

        #pragma omp parallel for schedule(static)
        for (int ii = 0; ii < static_cast<int>(N); ++ii) {
            int i = ii;
            const Particle& pi = particles[i];
            Vec2 force{0.0f, 0.0f};
            Vec2 pos = pi.position;
            int ix = static_cast<int>(std::floor(pos.x / s));
            int iy = static_cast<int>(std::floor(pos.y / s));
            ix = std::max(0, std::min(nx - 1, ix));
            iy = std::max(0, std::min(ny - 1, iy));
            int min_ix = std::max(0, ix - kr);
            int max_ix = std::min(nx - 1, ix + kr);
            int min_iy = std::max(0, iy - kr);
            int max_iy = std::min(ny - 1, iy + kr);

            for (int cy = min_iy; cy <= max_iy; ++cy) {
                for (int cx = min_ix; cx <= max_ix; ++cx) {
                    int bidx = cy * nx + cx;
                    const auto& neigh = buckets[bidx];
                    for (int j : neigh) {
                        if (j == i) continue;
                        Vec2 dir = particles[j].position - pos;
                        float dist2 = dir.length2();
                        float r2 = params.cullRadius * params.cullRadius;
                        float min_dist2 = 1e-6f;
                        if (dist2 < min_dist2 || dist2 > r2) continue;
                        float dist = std::sqrt(dist2);
                        dir *= (1.0f / dist);
                        float d = dist;
                        if (d < 0.1f) d = 0.1f;
                        const float G = 0.01f;
                        float scalar = pi.mass * particles[j].mass * (G / (d * d));
                        Vec2 force_add = dir * scalar;
                        if (dist > params.cullRadius * 0.75f) {
                            float decay = 1.0f - (dist - params.cullRadius * 0.75f) / (params.cullRadius * 0.25f);
                            force_add *= decay;
                        }
                        force += force_add;
                    }
                }
            }
            newParticles[i] = updateParticle(pi, force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}