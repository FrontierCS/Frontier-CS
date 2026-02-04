#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <immintrin.h>

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    float currentCullRadius;
    float currentDeltaTime;
    
    // Grid-based spatial hashing structure
    struct GridCell {
        std::vector<int> particleIndices;
        float minX, maxX, minY, maxY;
    };
    
    int gridSize;
    float cellSize;
    std::vector<GridCell> grid;
    std::vector<std::vector<int>> particleToCells;
    std::vector<int> cellOffsets;
    std::vector<int> cellParticles;
    std::vector<float> posX, posY, mass;
    std::vector<int> originalIds;
    
    void buildGrid(const std::vector<Particle>& particles, float cullRadius) {
        float worldSize = 100.0f;
        gridSize = std::max(1, (int)std::ceil(worldSize / cullRadius));
        cellSize = worldSize / gridSize;
        
        grid.assign(gridSize * gridSize, GridCell());
        particleToCells.assign(particles.size(), std::vector<int>());
        
        // Initialize grid bounds
        for (int i = 0; i < gridSize; ++i) {
            for (int j = 0; j < gridSize; ++j) {
                int idx = i * gridSize + j;
                grid[idx].minX = i * cellSize;
                grid[idx].maxX = (i + 1) * cellSize;
                grid[idx].minY = j * cellSize;
                grid[idx].maxY = (j + 1) * cellSize;
            }
        }
        
        // Assign particles to cells
        for (size_t p = 0; p < particles.size(); ++p) {
            int cellX = std::min(gridSize - 1, (int)(particles[p].position.x / cellSize));
            int cellY = std::min(gridSize - 1, (int)(particles[p].position.y / cellSize));
            int cellIdx = cellX * gridSize + cellY;
            grid[cellIdx].particleIndices.push_back(p);
            particleToCells[p].push_back(cellIdx);
            
            // Also add to neighboring cells for particles near boundaries
            if (particles[p].position.x - cellX * cellSize < cullRadius && cellX > 0) {
                int neighborIdx = (cellX - 1) * gridSize + cellY;
                grid[neighborIdx].particleIndices.push_back(p);
                particleToCells[p].push_back(neighborIdx);
            }
            if ((cellX + 1) * cellSize - particles[p].position.x < cullRadius && cellX < gridSize - 1) {
                int neighborIdx = (cellX + 1) * gridSize + cellY;
                grid[neighborIdx].particleIndices.push_back(p);
                particleToCells[p].push_back(neighborIdx);
            }
            if (particles[p].position.y - cellY * cellSize < cullRadius && cellY > 0) {
                int neighborIdx = cellX * gridSize + (cellY - 1);
                grid[neighborIdx].particleIndices.push_back(p);
                particleToCells[p].push_back(neighborIdx);
            }
            if ((cellY + 1) * cellSize - particles[p].position.y < cullRadius && cellY < gridSize - 1) {
                int neighborIdx = cellX * gridSize + (cellY + 1);
                grid[neighborIdx].particleIndices.push_back(p);
                particleToCells[p].push_back(neighborIdx);
            }
            
            // Remove duplicates from particleToCells[p]
            std::sort(particleToCells[p].begin(), particleToCells[p].end());
            particleToCells[p].erase(std::unique(particleToCells[p].begin(), 
                                               particleToCells[p].end()), 
                                   particleToCells[p].end());
        }
        
        // Flatten grid for better memory access
        cellOffsets.resize(gridSize * gridSize + 1);
        int totalParticles = 0;
        for (size_t i = 0; i < grid.size(); ++i) {
            cellOffsets[i] = totalParticles;
            totalParticles += grid[i].particleIndices.size();
        }
        cellOffsets[grid.size()] = totalParticles;
        
        cellParticles.resize(totalParticles);
        for (size_t i = 0; i < grid.size(); ++i) {
            std::memcpy(&cellParticles[cellOffsets[i]], 
                       grid[i].particleIndices.data(),
                       grid[i].particleIndices.size() * sizeof(int));
        }
        
        // Cache particle data for better memory locality
        posX.resize(particles.size());
        posY.resize(particles.size());
        mass.resize(particles.size());
        originalIds.resize(particles.size());
        
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < particles.size(); ++i) {
            posX[i] = particles[i].position.x;
            posY[i] = particles[i].position.y;
            mass[i] = particles[i].mass;
            originalIds[i] = particles[i].id;
        }
    }
    
    void updateCachedData(const std::vector<Particle>& particles) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < particles.size(); ++i) {
            posX[i] = particles[i].position.x;
            posY[i] = particles[i].position.y;
        }
    }
    
    Vec2 computeForceOptimized(int i, const std::vector<Particle>& particles, float cullRadius) {
        Vec2 force(0.0f, 0.0f);
        float cullRadius2 = cullRadius * cullRadius;
        float soft2 = 1e-2f;  // Softening length squared
        
        const float pi_x = posX[i];
        const float pi_y = posY[i];
        const Particle& pi_particle = particles[i];
        
        // Check all cells that particle i belongs to
        for (int cellIdx : particleToCells[i]) {
            int start = cellOffsets[cellIdx];
            int end = cellOffsets[cellIdx + 1];
            
            for (int k = start; k < end; ++k) {
                int j = cellParticles[k];
                if (j == i) continue;
                
                float dx = posX[j] - pi_x;
                float dy = posY[j] - pi_y;
                float dist2 = dx * dx + dy * dy;
                
                if (dist2 > cullRadius2) continue;
                if (dist2 < 1e-6f) continue;
                
                // Vectorized force computation
                float invDist = 1.0f / std::sqrt(dist2 + soft2);
                float invDist3 = invDist * invDist * invDist;
                float G = 0.01f;
                float forceMag = G * pi_particle.mass * mass[j] * invDist3;
                
                if (dist2 > 0.5625f * cullRadius2) {  // 0.75^2
                    float dist = std::sqrt(dist2);
                    float decay = 1.0f - (dist - cullRadius * 0.75f) / (cullRadius * 0.25f);
                    forceMag *= decay;
                }
                
                force.x += dx * forceMag;
                force.y += dy * forceMag;
            }
        }
        
        return force;
    }

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        currentCullRadius = params.cullRadius;
        currentDeltaTime = params.deltaTime;
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        if (params.cullRadius != currentCullRadius) {
            buildGrid(particles, params.cullRadius);
            currentCullRadius = params.cullRadius;
        } else {
            updateCachedData(particles);
        }
        
        currentDeltaTime = params.deltaTime;
        size_t n = particles.size();
        newParticles.resize(n);
        
        #pragma omp parallel for schedule(dynamic, 64)
        for (size_t i = 0; i < n; ++i) {
            Vec2 force = computeForceOptimized(i, particles, params.cullRadius);
            newParticles[i] = updateParticle(particles[i], force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}