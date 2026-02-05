// Optimized reference using spatial grid partitioning
// Significantly faster than O(N²) baseline when cullRadius << space_size

#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    float cellSize;
    int gridWidth, gridHeight;
    float minX, minY, maxX, maxY;
    std::vector<std::vector<int>> grid;
    std::vector<std::vector<int>> threadGrids;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        cellSize = 0;  // Will be set in simulateStep
    }

    void buildGrid(const std::vector<Particle>& particles, float cullRadius) {
        // Find bounds
        minX = minY = 1e9f;
        maxX = maxY = -1e9f;
        for (const auto& p : particles) {
            minX = std::min(minX, p.position.x);
            minY = std::min(minY, p.position.y);
            maxX = std::max(maxX, p.position.x);
            maxY = std::max(maxY, p.position.y);
        }

        // Add padding
        minX -= cullRadius;
        minY -= cullRadius;
        maxX += cullRadius;
        maxY += cullRadius;

        gridWidth = (int)std::ceil((maxX - minX) / cellSize) + 1;
        gridHeight = (int)std::ceil((maxY - minY) / cellSize) + 1;

        // Resize and clear grid
        grid.resize(gridWidth * gridHeight);
        for (auto& cell : grid) cell.clear();

        // Insert particles into grid
        for (size_t i = 0; i < particles.size(); i++) {
            int cx = (int)((particles[i].position.x - minX) / cellSize);
            int cy = (int)((particles[i].position.y - minY) / cellSize);
            cx = std::max(0, std::min(cx, gridWidth - 1));
            cy = std::max(0, std::min(cy, gridHeight - 1));
            grid[cy * gridWidth + cx].push_back(i);
        }
    }

    void simulateStep(std::vector<Particle>& particles,
                      std::vector<Particle>& newParticles,
                      StepParameters params) override {
        cellSize = params.cullRadius;
        buildGrid(particles, params.cullRadius);

        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < (int)particles.size(); i++) {
            const auto& pi = particles[i];
            Vec2 force(0.0f, 0.0f);

            // Get cell coordinates
            int cx = (int)((pi.position.x - minX) / cellSize);
            int cy = (int)((pi.position.y - minY) / cellSize);
            cx = std::max(0, std::min(cx, gridWidth - 1));
            cy = std::max(0, std::min(cy, gridHeight - 1));

            // Check neighboring cells (3x3)
            for (int dy = -1; dy <= 1; dy++) {
                int ny = cy + dy;
                if (ny < 0 || ny >= gridHeight) continue;

                for (int dx = -1; dx <= 1; dx++) {
                    int nx = cx + dx;
                    if (nx < 0 || nx >= gridWidth) continue;

                    const auto& cell = grid[ny * gridWidth + nx];
                    for (int j : cell) {
                        if (j == i) continue;
                        if ((pi.position - particles[j].position).length() < params.cullRadius) {
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
