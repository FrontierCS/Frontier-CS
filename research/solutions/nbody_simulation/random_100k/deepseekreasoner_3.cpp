#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <memory>
#include <cstring>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    float cullRadius = 1.0f;
    
    struct GridCell {
        std::vector<int> particleIndices;
        void clear() { particleIndices.clear(); }
        void add(int idx) { particleIndices.push_back(idx); }
    };
    
    float gridSize;
    int gridDim;
    std::vector<GridCell> grid;
    std::vector<int> cellOffsets;
    
    void buildGrid(const std::vector<Particle>& particles) {
        for (auto& cell : grid) cell.clear();
        
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < (int)particles.size(); i++) {
            const auto& p = particles[i];
            int cx = std::clamp((int)(p.position.x / gridSize), 0, gridDim - 1);
            int cy = std::clamp((int)(p.position.y / gridSize), 0, gridDim - 1);
            int cellIdx = cy * gridDim + cx;
            
            #pragma omp critical
            grid[cellIdx].add(i);
        }
        
        cellOffsets[0] = 0;
        for (int i = 1; i <= gridDim * gridDim; i++) {
            cellOffsets[i] = cellOffsets[i-1] + grid[i-1].particleIndices.size();
        }
        
        std::vector<int> flatIndices(cellOffsets.back());
        
        #pragma omp parallel for schedule(static)
        for (int cell = 0; cell < gridDim * gridDim; cell++) {
            int offset = cellOffsets[cell];
            const auto& indices = grid[cell].particleIndices;
            std::copy(indices.begin(), indices.end(), flatIndices.begin() + offset);
        }
        
        for (int cell = 0; cell < gridDim * gridDim; cell++) {
            grid[cell].particleIndices.clear();
            int start = cellOffsets[cell];
            int end = cellOffsets[cell + 1];
            grid[cell].particleIndices.assign(flatIndices.begin() + start, flatIndices.begin() + end);
        }
    }
    
public:
    void init(int numParticles, StepParameters params) override {
        cullRadius = params.cullRadius;
        gridSize = cullRadius;
        gridDim = (int)std::ceil(100.0f / gridSize) + 1;
        grid.resize(gridDim * gridDim);
        cellOffsets.resize(gridDim * gridDim + 1);
        omp_set_num_threads(numThreads);
    }
    
    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        cullRadius = params.cullRadius;
        
        buildGrid(particles);
        
        float cullRadius2 = cullRadius * cullRadius;
        int searchRange = (int)std::ceil(cullRadius / gridSize) + 1;
        
        #pragma omp parallel for schedule(dynamic, 32)
        for (int i = 0; i < (int)particles.size(); i++) {
            const auto& pi = particles[i];
            Vec2 force(0.0f, 0.0f);
            
            int cx = std::clamp((int)(pi.position.x / gridSize), 0, gridDim - 1);
            int cy = std::clamp((int)(pi.position.y / gridSize), 0, gridDim - 1);
            
            for (int dy = -searchRange; dy <= searchRange; dy++) {
                int cellY = cy + dy;
                if (cellY < 0 || cellY >= gridDim) continue;
                
                for (int dx = -searchRange; dx <= searchRange; dx++) {
                    int cellX = cx + dx;
                    if (cellX < 0 || cellX >= gridDim) continue;
                    
                    int cellIdx = cellY * gridDim + cellX;
                    const auto& indices = grid[cellIdx].particleIndices;
                    
                    for (int j : indices) {
                        if (j == i) continue;
                        
                        const auto& pj = particles[j];
                        Vec2 dir = pj.position - pi.position;
                        float dist2 = dir.x * dir.x + dir.y * dir.y;
                        
                        if (dist2 < 1e-6f || dist2 > cullRadius2) continue;
                        
                        force += computeForce(pi, pj, cullRadius);
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