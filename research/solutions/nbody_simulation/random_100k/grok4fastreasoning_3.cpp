#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
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
        if (particles.empty()) {
            newParticles.clear();
            return;
        }
        size_t N = particles.size();
        newParticles.resize(N);

        float min_x = particles[0].position.x;
        float max_x = min_x;
        float min_y = particles[0].position.y;
        float max_y = min_y;
        for (const auto& p : particles) {
            min_x = std::min(min_x, p.position.x);
            max_x = std::max(max_x, p.position.x);
            min_y = std::min(min_y, p.position.y);
            max_y = std::max(max_y, p.position.y);
        }
        float width_x = max_x - min_x;
        float width_y = max_y - min_y;
        const float CELL_SIZE = 5.0f;
        int nx = static_cast<int>(std::floor(width_x / CELL_SIZE)) + 1;
        int ny = static_cast<int>(std::floor(width_y / CELL_SIZE)) + 1;
        if (nx <= 0) nx = 1;
        if (ny <= 0) ny = 1;

        std::vector<std::vector<std::vector<int>>> cell_lists(
            nx, std::vector<std::vector<int>>(ny));
        for (size_t i = 0; i < N; ++i) {
            const auto& p = particles[i];
            int ix = static_cast<int>(std::floor((p.position.x - min_x) / CELL_SIZE));
            int iy = static_cast<int>(std::floor((p.position.y - min_y) / CELL_SIZE));
            cell_lists[ix][iy].push_back(static_cast<int>(i));
        }

        int k = static_cast<int>(std::ceil(params.cullRadius / CELL_SIZE)) + 1;
        float r2 = params.cullRadius * params.cullRadius;
        float eps2 = 1e-6f;

#pragma omp parallel for schedule(dynamic, 1000)
        for (int i = 0; i < static_cast<int>(N); ++i) {
            const Particle& pi = particles[i];
            Vec2 force(0.0f, 0.0f);
            int ix = static_cast<int>(std::floor((pi.position.x - min_x) / CELL_SIZE));
            int iy = static_cast<int>(std::floor((pi.position.y - min_y) / CELL_SIZE));
            int start_ix = std::max(0, ix - k);
            int end_ix = std::min(nx - 1, ix + k);
            int start_iy = std::max(0, iy - k);
            int end_iy = std::min(ny - 1, iy + k);
            for (int cix = start_ix; cix <= end_ix; ++cix) {
                for (int ciy = start_iy; ciy <= end_iy; ++ciy) {
                    for (int j : cell_lists[cix][ciy]) {
                        if (j == i) continue;
                        Vec2 dir = particles[j].position - pi.position;
                        float dist2 = dir.length2();
                        if (dist2 > r2 || dist2 < eps2) continue;
                        force += computeForce(pi, particles[j], params.cullRadius);
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