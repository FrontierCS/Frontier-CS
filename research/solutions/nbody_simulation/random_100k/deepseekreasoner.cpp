#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <array>
#include <cstdint>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    float cellSize;
    int gridWidth, gridHeight;
    std::vector<std::vector<int>> gridCells;
    std::vector<int> cellOffsets;
    std::vector<int> particleIndices;
    std::vector<std::array<int, 2>> cellCoords;
    std::vector<Vec2> forces;
    std::vector<std::vector<int>> threadLocalForces;

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        forces.resize(numParticles);
        threadLocalForces.resize(numThreads);
        for (auto& tl : threadLocalForces) {
            tl.resize(numParticles);
        }
        
        // Setup spatial grid
        cellSize = params.cullRadius;
        gridWidth = static_cast<int>(100.0f / cellSize) + 1;
        gridHeight = static_cast<int>(100.0f / cellSize) + 1;
        gridCells.resize(gridWidth * gridHeight);
        cellOffsets.resize(gridWidth * gridHeight + 1);
        particleIndices.resize(numParticles);
        cellCoords.resize(numParticles);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = particles.size();
        const float cullRadius = params.cullRadius;
        const float cullRadius2 = cullRadius * cullRadius;
        
        // Reset forces
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            forces[i] = Vec2{0.0f, 0.0f};
        }
        
        // Assign particles to grid cells
        #pragma omp parallel
        {
            std::vector<int> localCounts(gridCells.size(), 0);
            #pragma omp for
            for (int i = 0; i < N; i++) {
                int cx = static_cast<int>(particles[i].position.x / cellSize);
                int cy = static_cast<int>(particles[i].position.y / cellSize);
                cx = std::max(0, std::min(gridWidth - 1, cx));
                cy = std::max(0, std::min(gridHeight - 1, cy));
                int cellIdx = cy * gridWidth + cx;
                cellCoords[i] = {cx, cy};
                #pragma omp atomic
                localCounts[cellIdx]++;
            }
            
            #pragma omp barrier
            
            // Prefix sum for offsets
            #pragma omp single
            {
                cellOffsets[0] = 0;
                for (size_t i = 0; i < gridCells.size(); i++) {
                    cellOffsets[i + 1] = cellOffsets[i] + localCounts[i];
                }
            }
            
            #pragma omp barrier
            
            // Place particles in cells
            std::vector<int> writePtrs = cellOffsets;
            #pragma omp for
            for (int i = 0; i < N; i++) {
                int cx = cellCoords[i][0];
                int cy = cellCoords[i][1];
                int cellIdx = cy * gridWidth + cx;
                int pos = writePtrs[cellIdx]++;
                particleIndices[pos] = i;
            }
        }
        
        // Compute forces using spatial grid
        #pragma omp parallel
        {
            int tid = omp_get_thread_num();
            auto& tlForces = threadLocalForces[tid];
            std::fill(tlForces.begin(), tlForces.begin() + N, 0);
            
            #pragma omp for schedule(dynamic, 32)
            for (int cellIdx = 0; cellIdx < static_cast<int>(gridCells.size()); cellIdx++) {
                int cx = cellIdx % gridWidth;
                int cy = cellIdx / gridWidth;
                int start = cellOffsets[cellIdx];
                int end = cellOffsets[cellIdx + 1];
                
                for (int dx = -1; dx <= 1; dx++) {
                    for (int dy = -1; dy <= 1; dy++) {
                        int nx = cx + dx;
                        int ny = cy + dy;
                        if (nx >= 0 && nx < gridWidth && ny >= 0 && ny < gridHeight) {
                            int neighborIdx = ny * gridWidth + nx;
                            int nStart = cellOffsets[neighborIdx];
                            int nEnd = cellOffsets[neighborIdx + 1];
                            
                            for (int i = start; i < end; i++) {
                                int piIdx = particleIndices[i];
                                const Particle& pi = particles[piIdx];
                                Vec2 forceSum{0.0f, 0.0f};
                                
                                for (int j = nStart; j < nEnd; j++) {
                                    int pjIdx = particleIndices[j];
                                    if (piIdx == pjIdx) continue;
                                    
                                    const Particle& pj = particles[pjIdx];
                                    Vec2 dir = pj.position - pi.position;
                                    float dist2 = dir.x * dir.x + dir.y * dir.y;
                                    
                                    if (dist2 < cullRadius2 && dist2 > 1e-6f) {
                                        forceSum += computeForce(pi, pj, cullRadius);
                                        tlForces[pjIdx] = 1;
                                    }
                                }
                                
                                #pragma omp atomic
                                forces[piIdx].x += forceSum.x;
                                #pragma omp atomic
                                forces[piIdx].y += forceSum.y;
                            }
                        }
                    }
                }
            }
            
            // Update particles
            #pragma omp for
            for (int i = 0; i < N; i++) {
                if (tlForces[i]) {
                    newParticles[i] = updateParticle(particles[i], forces[i], params.deltaTime);
                } else {
                    newParticles[i] = updateParticle(particles[i], Vec2{0.0f, 0.0f}, params.deltaTime);
                }
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}