#include "world.h"
#include <omp.h>
#include <cmath>
#include <vector>
#include <algorithm>
#include <memory>
#include <unordered_map>
#include <immintrin.h>
#include <xmmintrin.h>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    float cellSize;
    float invCellSize;
    float cullRadius;
    float cullRadiusSq;
    
    struct Cell {
        std::vector<int> particles;
        float minX, minY, maxX, maxY;
    };
    
    struct Grid {
        int gridX, gridY;
        std::vector<Cell> cells;
        
        Grid(float worldSize, float cellSize) {
            gridX = gridY = static_cast<int>(std::ceil(worldSize / cellSize));
            cells.resize(gridX * gridY);
            for (int y = 0; y < gridY; ++y) {
                for (int x = 0; x < gridX; ++x) {
                    auto& cell = cells[y * gridX + x];
                    cell.minX = x * cellSize;
                    cell.minY = y * cellSize;
                    cell.maxX = (x + 1) * cellSize;
                    cell.maxY = (y + 1) * cellSize;
                }
            }
        }
        
        inline int getCellIdx(float x, float y) const {
            int cx = static_cast<int>(x * invCellSize);
            int cy = static_cast<int>(y * invCellSize);
            cx = std::max(0, std::min(cx, gridX - 1));
            cy = std::max(0, std::min(cy, gridY - 1));
            return cy * gridX + cx;
        }
        
        void clear() {
            for (auto& cell : cells) {
                cell.particles.clear();
            }
        }
    };
    
    std::unique_ptr<Grid> grid;
    std::vector<Vec2> forces;
    std::vector<int> cellOffsets;
    std::vector<int> cellParticleIndices;
    std::vector<int> particleToCell;
    
    static constexpr float WORLD_SIZE = 100.0f;
    static constexpr float G = 0.01f;
    
public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        cullRadius = params.cullRadius;
        cullRadiusSq = cullRadius * cullRadius;
        cellSize = cullRadius;
        invCellSize = 1.0f / cellSize;
        grid = std::make_unique<Grid>(WORLD_SIZE, cellSize);
        forces.resize(numParticles);
        particleToCell.resize(numParticles);
    }
    
    void buildGrid(const std::vector<Particle>& particles) {
        grid->clear();
        
        #pragma omp parallel
        {
            std::vector<std::vector<int>> localCells(grid->cells.size());
            
            #pragma omp for schedule(static)
            for (int i = 0; i < (int)particles.size(); ++i) {
                const auto& p = particles[i];
                int cellIdx = grid->getCellIdx(p.position.x, p.position.y);
                localCells[cellIdx].push_back(i);
                particleToCell[i] = cellIdx;
            }
            
            #pragma omp for schedule(static)
            for (int i = 0; i < (int)grid->cells.size(); ++i) {
                for (int t = 0; t < numThreads; ++t) {
                    grid->cells[i].particles.insert(
                        grid->cells[i].particles.end(),
                        localCells[i].begin(),
                        localCells[i].end()
                    );
                }
            }
        }
        
        cellOffsets.resize(grid->cells.size() + 1);
        cellOffsets[0] = 0;
        for (size_t i = 0; i < grid->cells.size(); ++i) {
            cellOffsets[i + 1] = cellOffsets[i] + (int)grid->cells[i].particles.size();
        }
        
        cellParticleIndices.resize(particles.size());
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < (int)grid->cells.size(); ++i) {
            const auto& cell = grid->cells[i];
            int base = cellOffsets[i];
            for (int j = 0; j < (int)cell.particles.size(); ++j) {
                cellParticleIndices[base + j] = cell.particles[j];
            }
        }
    }
    
    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        cullRadius = params.cullRadius;
        cullRadiusSq = cullRadius * cullRadius;
        
        buildGrid(particles);
        
        #pragma omp parallel
        {
            #pragma omp for schedule(dynamic, 64)
            for (int cellIdx = 0; cellIdx < (int)grid->cells.size(); ++cellIdx) {
                int start = cellOffsets[cellIdx];
                int end = cellOffsets[cellIdx + 1];
                
                int cx = cellIdx % grid->gridX;
                int cy = cellIdx / grid->gridX;
                
                for (int i = start; i < end; ++i) {
                    int pi_idx = cellParticleIndices[i];
                    const Particle& pi = particles[pi_idx];
                    Vec2 force(0.0f, 0.0f);
                    
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            int nx = cx + dx;
                            int ny = cy + dy;
                            
                            if (nx >= 0 && nx < grid->gridX && ny >= 0 && ny < grid->gridY) {
                                int ncellIdx = ny * grid->gridX + nx;
                                int nstart = cellOffsets[ncellIdx];
                                int nend = cellOffsets[ncellIdx + 1];
                                
                                for (int j = nstart; j < nend; ++j) {
                                    int pj_idx = cellParticleIndices[j];
                                    if (pi_idx == pj_idx) continue;
                                    
                                    const Particle& pj = particles[pj_idx];
                                    float dx_pos = pj.position.x - pi.position.x;
                                    float dy_pos = pj.position.y - pi.position.y;
                                    float distSq = dx_pos * dx_pos + dy_pos * dy_pos;
                                    
                                    if (distSq < cullRadiusSq && distSq > 1e-6f) {
                                        float dist = std::sqrt(distSq);
                                        if (dist < 1e-3f) continue;
                                        
                                        float invDist = 1.0f / dist;
                                        dx_pos *= invDist;
                                        dy_pos *= invDist;
                                        
                                        float forceMag = pi.mass * pj.mass * G / (distSq);
                                        if (dist > cullRadius * 0.75f) {
                                            float decay = 1.0f - (dist - cullRadius * 0.75f) / (cullRadius * 0.25f);
                                            forceMag *= decay;
                                        }
                                        
                                        force.x += dx_pos * forceMag;
                                        force.y += dy_pos * forceMag;
                                    }
                                }
                            }
                        }
                    }
                    
                    forces[pi_idx] = force;
                }
            }
            
            #pragma omp for schedule(static)
            for (int i = 0; i < (int)particles.size(); ++i) {
                newParticles[i] = updateParticle(particles[i], forces[i], params.deltaTime);
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}