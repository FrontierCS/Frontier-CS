#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>

class MySimulator : public Simulator {
private:
    int numThreads;

    // Grid parameters
    int gridSizeX = 0;
    int gridSizeY = 0;
    int numCells = 0;
    int cellRadius = 0;
    float cellSize = 1.0f;
    float invCellSize = 1.0f;

    // Persistent buffers
    std::vector<int> particleCellX;
    std::vector<int> particleCellY;
    std::vector<int> cellStart;           // starting index in cellParticleIndices
    std::vector<int> cellCount;           // temporary counts per cell
    std::vector<int> cellNext;            // for filling indices
    std::vector<int> cellParticleIndices; // indices of particles by cell

public:
    MySimulator() {
        numThreads = omp_get_max_threads();
    }

    void init(int numParticles, StepParameters params) override {
        numThreads = omp_get_max_threads();
        omp_set_num_threads(numThreads);

        particleCellX.resize(numParticles);
        particleCellY.resize(numParticles);
        cellParticleIndices.resize(numParticles);
        cellStart.clear();
        cellCount.clear();
        cellNext.clear();
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = static_cast<int>(particles.size());
        if (N == 0) return;
        if (static_cast<int>(newParticles.size()) < N)
            newParticles.resize(N);

        // 1. Compute bounding box (sequential, negligible vs force computations)
        float minx = particles[0].position.x;
        float maxx = minx;
        float miny = particles[0].position.y;
        float maxy = miny;
        for (int i = 1; i < N; ++i) {
            float x = particles[i].position.x;
            float y = particles[i].position.y;
            if (x < minx) minx = x;
            if (x > maxx) maxx = x;
            if (y < miny) miny = y;
            if (y > maxy) maxy = y;
        }

        float width = maxx - minx;
        float height = maxy - miny;
        if (width < 1e-3f) width = 1e-3f;
        if (height < 1e-3f) height = 1e-3f;
        float area = width * height;

        const float R = params.cullRadius;
        const float R2 = R * R;

        // 2. Choose cell size based on desired particles per cell, clamped by cullRadius
        const float targetParticlesPerCell = 32.0f;
        float estCellArea = area * targetParticlesPerCell / static_cast<float>(N);
        if (estCellArea < 1e-4f) estCellArea = 1e-4f;
        float chosenCellSize = std::sqrt(estCellArea);
        if (chosenCellSize > R) chosenCellSize = R;
        // Avoid extremely tiny cells for numerical stability
        if (chosenCellSize < R * 0.05f) chosenCellSize = R * 0.05f;
        if (chosenCellSize < 1e-3f) chosenCellSize = 1e-3f;

        cellSize = chosenCellSize;
        invCellSize = 1.0f / cellSize;

        gridSizeX = static_cast<int>(std::ceil(width * invCellSize));
        gridSizeY = static_cast<int>(std::ceil(height * invCellSize));
        if (gridSizeX < 1) gridSizeX = 1;
        if (gridSizeY < 1) gridSizeY = 1;
        numCells = gridSizeX * gridSizeY;

        cellRadius = static_cast<int>(std::ceil(R * invCellSize));
        if (cellRadius < 1) cellRadius = 1;

        // Ensure buffers have enough capacity
        if (static_cast<int>(cellCount.size()) < numCells) {
            cellCount.assign(numCells, 0);
        } else {
            std::fill(cellCount.begin(), cellCount.begin() + numCells, 0);
        }
        if (static_cast<int>(cellStart.size()) < numCells)
            cellStart.resize(numCells);
        if (static_cast<int>(cellNext.size()) < numCells)
            cellNext.resize(numCells);
        if (static_cast<int>(cellParticleIndices.size()) < N)
            cellParticleIndices.resize(N);
        if (static_cast<int>(particleCellX.size()) < N)
            particleCellX.resize(N);
        if (static_cast<int>(particleCellY.size()) < N)
            particleCellY.resize(N);

        // 3. Assign particles to cells and count per-cell occupancy
        for (int i = 0; i < N; ++i) {
            float fx = (particles[i].position.x - minx) * invCellSize;
            float fy = (particles[i].position.y - miny) * invCellSize;
            int cx = static_cast<int>(fx);
            int cy = static_cast<int>(fy);
            if (cx < 0) cx = 0;
            else if (cx >= gridSizeX) cx = gridSizeX - 1;
            if (cy < 0) cy = 0;
            else if (cy >= gridSizeY) cy = gridSizeY - 1;

            particleCellX[i] = cx;
            particleCellY[i] = cy;
            int cellId = cy * gridSizeX + cx;
            ++cellCount[cellId];
        }

        // 4. Build prefix sums to compute cellStart
        int sum = 0;
        for (int c = 0; c < numCells; ++c) {
            cellStart[c] = sum;
            sum += cellCount[c];
        }
        // sum should equal N

        // 5. Fill cellParticleIndices with particle indices
        for (int c = 0; c < numCells; ++c)
            cellNext[c] = cellStart[c];

        for (int i = 0; i < N; ++i) {
            int cx = particleCellX[i];
            int cy = particleCellY[i];
            int cellId = cy * gridSizeX + cx;
            int idx = cellNext[cellId]++;
            cellParticleIndices[idx] = i;
        }

        // 6. Compute forces in parallel
        const int localGridSizeX = gridSizeX;
        const int localGridSizeY = gridSizeY;
        const int localNumCells = numCells;
        const int localRadius = cellRadius;
        const float localR = R;
        const float localR2 = R2;

        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; ++i) {
            const Particle &pi = particles[i];
            Vec2 force(0.0f, 0.0f);

            int cx = particleCellX[i];
            int cy = particleCellY[i];

            int minCellY = cy - localRadius;
            if (minCellY < 0) minCellY = 0;
            int maxCellY = cy + localRadius;
            if (maxCellY >= localGridSizeY) maxCellY = localGridSizeY - 1;

            int minCellX = cx - localRadius;
            if (minCellX < 0) minCellX = 0;
            int maxCellX = cx + localRadius;
            if (maxCellX >= localGridSizeX) maxCellX = localGridSizeX - 1;

            for (int ny = minCellY; ny <= maxCellY; ++ny) {
                int baseIdx = ny * localGridSizeX;
                for (int nx = minCellX; nx <= maxCellX; ++nx) {
                    int cellId = baseIdx + nx;
                    int start = cellStart[cellId];
                    int end = (cellId + 1 < localNumCells) ? cellStart[cellId + 1] : N;

                    for (int idx = start; idx < end; ++idx) {
                        int j = cellParticleIndices[idx];
                        if (j == i) continue;

                        const Particle &pj = particles[j];

                        float dx = pj.position.x - pi.position.x;
                        if (dx > localR || dx < -localR) continue;
                        float dy = pj.position.y - pi.position.y;
                        if (dy > localR || dy < -localR) continue;

                        float dist2 = dx * dx + dy * dy;
                        if (dist2 >= localR2) continue;

                        force += computeForce(pi, pj, localR);
                    }
                }
            }

            newParticles[i] = updateParticle(pi, force, params.deltaTime);
        }
    }
};

// Factory function - must be implemented
Simulator* createSimulator() {
    return new MySimulator();
}