#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>

class MySimulator : public Simulator {
private:
    int numThreads = 16;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        float R = params.cullRadius;
        float cell_size = R / 5.0f;
        const int NUM_BINS = 41;
        const int OFFSET = 20;
        const int total_cells = NUM_BINS * NUM_BINS;
        std::vector<std::vector<int>> grid(total_cells);
        for (auto& cell : grid) {
            cell.reserve(20);
        }

        auto get_bin = [&](float p, float cs) -> int {
            int b = static_cast<int>(std::floor(p / cs)) + OFFSET;
            if (b < 0) return 0;
            if (b >= NUM_BINS) return NUM_BINS - 1;
            return b;
        };

        // Build grid
        for (size_t i = 0; i < particles.size(); ++i) {
            float px = particles[i].position.x;
            float py = particles[i].position.y;
            int bx = get_bin(px, cell_size);
            int by = get_bin(py, cell_size);
            int cid = bx * NUM_BINS + by;
            grid[cid].push_back(static_cast<int>(i));
        }

        const float G = 0.01f;
        const float EPS2 = 1e-6f;
        const float SOFTEN = 0.1f;

        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < static_cast<int>(particles.size()); ++i) {
            const Particle& pi = particles[i];
            Vec2 force{0.0f, 0.0f};
            float px = pi.position.x;
            float py = pi.position.y;

            int min_bx = static_cast<int>(std::floor((px - R) / cell_size)) + OFFSET;
            int max_bx = static_cast<int>(std::floor((px + R) / cell_size)) + OFFSET;
            int min_by = static_cast<int>(std::floor((py - R) / cell_size)) + OFFSET;
            int max_by = static_cast<int>(std::floor((py + R) / cell_size)) + OFFSET;

            min_bx = std::max(0, min_bx);
            max_bx = std::min(NUM_BINS - 1, max_bx);
            min_by = std::max(0, min_by);
            max_by = std::min(NUM_BINS - 1, max_by);

            for (int bx = min_bx; bx <= max_bx; ++bx) {
                for (int by = min_by; by <= max_by; ++by) {
                    int cid = bx * NUM_BINS + by;
                    for (int j : grid[cid]) {
                        if (j == i) continue;
                        const Particle& pj = particles[j];
                        Vec2 dir = pj.position - pi.position;
                        float dist2 = dir.x * dir.x + dir.y * dir.y;
                        if (dist2 < EPS2 || dist2 > R * R) continue;
                        float dist = std::sqrt(dist2);
                        float inv_dist = 1.0f / dist;
                        dir.x *= inv_dist;
                        dir.y *= inv_dist;
                        float d = dist;
                        if (d < SOFTEN) d = SOFTEN;
                        float mag = pi.mass * pj.mass * (G / (d * d));
                        Vec2 f{dir.x * mag, dir.y * mag};
                        if (dist > R * 0.75f) {
                            float decay = 1.0f - (dist - R * 0.75f) / (R * 0.25f);
                            if (decay < 0.0f) decay = 0.0f;
                            f.x *= decay;
                            f.y *= decay;
                        }
                        force.x += f.x;
                        force.y += f.y;
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