#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <limits>

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
        size_t N = particles.size();
        newParticles.resize(N);
        if (N == 0) return;

        int N_ = static_cast<int>(N);

        // Compute bounds
        float min_x = std::numeric_limits<float>::max();
        float max_x = std::numeric_limits<float>::lowest();
        float min_y = min_x;
        float max_y = max_x;
        for (const auto& p : particles) {
            float x = p.position.x;
            float y = p.position.y;
            if (x < min_x) min_x = x;
            if (x > max_x) max_x = x;
            if (y < min_y) min_y = y;
            if (y > max_y) max_y = y;
        }

        float cell_size = params.cullRadius / 2.0f;
        float span_x = max_x - min_x;
        int num_cols = 1;
        if (span_x > 0.0f) {
            num_cols = static_cast<int>(std::floor(span_x / cell_size)) + 1;
        }
        float span_y = max_y - min_y;
        int num_rows = 1;
        if (span_y > 0.0f) {
            num_rows = static_cast<int>(std::floor(span_y / cell_size)) + 1;
        }
        int total_cells = num_rows * num_cols;

        std::vector<int> cell_ids(N_);
        #pragma omp parallel for
        for (int i = 0; i < N_; ++i) {
            float dx = (particles[i].position.x - min_x) / cell_size;
            float dy = (particles[i].position.y - min_y) / cell_size;
            int col = static_cast<int>(std::floor(dx));
            int row = static_cast<int>(std::floor(dy));
            col = std::max(0, std::min(num_cols - 1, col));
            row = std::max(0, std::min(num_rows - 1, row));
            cell_ids[i] = row * num_cols + col;
        }

        std::vector<std::vector<int>> grid(total_cells);
        for (int i = 0; i < N_; ++i) {
            grid[cell_ids[i]].push_back(i);
        }

        float cull2 = params.cullRadius * params.cullRadius;
        float eps2 = 1e-6f;
        int search_dist = static_cast<int>(std::ceil(params.cullRadius / cell_size));

        #pragma omp parallel for schedule(dynamic, 256)
        for (int i = 0; i < N_; ++i) {
            const Particle& pi = particles[i];
            Vec2 force{0.0f, 0.0f};

            float dx = (pi.position.x - min_x) / cell_size;
            float dy = (pi.position.y - min_y) / cell_size;
            int col = static_cast<int>(std::floor(dx));
            int row = static_cast<int>(std::floor(dy));
            col = std::max(0, std::min(num_cols - 1, col));
            row = std::max(0, std::min(num_rows - 1, row));

            for (int drow = -search_dist; drow <= search_dist; ++drow) {
                int trow = row + drow;
                if (trow < 0 || trow >= num_rows) continue;
                for (int dcol = -search_dist; dcol <= search_dist; ++dcol) {
                    int tcol = col + dcol;
                    if (tcol < 0 || tcol >= num_cols) continue;
                    int tcell = trow * num_cols + tcol;
                    for (int j : grid[tcell]) {
                        if (j == i) continue;
                        Vec2 dir = particles[j].position - pi.position;
                        float dist2 = dir.length2();
                        if (dist2 > eps2 && dist2 < cull2) {
                            force += computeForce(pi, particles[j], params.cullRadius);
                        }
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