#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>

class MySimulator : public Simulator {
private:
    int numThreads;
    float cellSizeFactor;
    std::vector<int> cellCounts;
    std::vector<int> cellOffsets;
    std::vector<int> sortedIndices;
    std::vector<int> particleCells;

public:
    MySimulator()
        : numThreads(omp_get_max_threads()), cellSizeFactor(0.1f) {}

    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        sortedIndices.resize(numParticles);
        particleCells.resize(numParticles);
        // cellCounts and cellOffsets will be sized when grid dimensions are known
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = static_cast<int>(particles.size());
        if (n == 0)
            return;

        if (static_cast<int>(newParticles.size()) < n)
            newParticles.resize(n);

        Particle *pData = particles.data();
        Particle *outData = newParticles.data();

        // Compute bounding box
        float minX = pData[0].position.x;
        float maxX = pData[0].position.x;
        float minY = pData[0].position.y;
        float maxY = pData[0].position.y;

        for (int i = 1; i < n; ++i) {
            const float x = pData[i].position.x;
            const float y = pData[i].position.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        float widthX = maxX - minX;
        float widthY = maxY - minY;
        if (widthX < 1e-3f) widthX = 1e-3f;
        if (widthY < 1e-3f) widthY = 1e-3f;

        const float R = params.cullRadius;
        float cellSize = R * cellSizeFactor;
        if (cellSize < 1e-3f || cellSize > R) {
            cellSize = R;
        }
        const float invCellSize = 1.0f / cellSize;

        int gridW = static_cast<int>(std::ceil(widthX * invCellSize));
        int gridH = static_cast<int>(std::ceil(widthY * invCellSize));
        if (gridW < 1) gridW = 1;
        if (gridH < 1) gridH = 1;
        int numCells = gridW * gridH;

        if (static_cast<int>(cellCounts.size()) < numCells) {
            cellCounts.assign(numCells, 0);
            cellOffsets.resize(numCells + 1);
        } else {
            std::fill(cellCounts.begin(), cellCounts.begin() + numCells, 0);
            if (static_cast<int>(cellOffsets.size()) < numCells + 1)
                cellOffsets.resize(numCells + 1);
        }

        if (static_cast<int>(sortedIndices.size()) < n)
            sortedIndices.resize(n);
        if (static_cast<int>(particleCells.size()) < n)
            particleCells.resize(n);

        // First pass: assign particles to cells and count
        for (int i = 0; i < n; ++i) {
            float fx = (pData[i].position.x - minX) * invCellSize;
            float fy = (pData[i].position.y - minY) * invCellSize;
            int ix = static_cast<int>(fx);
            int iy = static_cast<int>(fy);
            if (ix < 0) ix = 0;
            else if (ix >= gridW) ix = gridW - 1;
            if (iy < 0) iy = 0;
            else if (iy >= gridH) iy = gridH - 1;
            int cellIdx = iy * gridW + ix;
            particleCells[i] = cellIdx;
            cellCounts[cellIdx]++;
        }

        // Prefix sum to get cell offsets
        cellOffsets[0] = 0;
        for (int c = 0; c < numCells; ++c) {
            cellOffsets[c + 1] = cellOffsets[c] + cellCounts[c];
        }

        // Reset counts to use as cursors when filling sortedIndices
        std::fill(cellCounts.begin(), cellCounts.begin() + numCells, 0);

        // Fill sortedIndices with particle indices grouped by cell
        for (int i = 0; i < n; ++i) {
            int cellIdx = particleCells[i];
            int dst = cellOffsets[cellIdx] + cellCounts[cellIdx]++;
            sortedIndices[dst] = i;
        }

        const int neighborRange = static_cast<int>(std::ceil(R / cellSize));
        const float R2 = R * R;
        const float dt = params.deltaTime;

        // Compute forces and integrate
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < n; ++i) {
            const Particle pi = pData[i];
            const float pix = pi.position.x;
            const float piy = pi.position.y;

            Vec2 totalForce(0.0f, 0.0f);

            const int cellIdx = particleCells[i];
            const int ix = cellIdx % gridW;
            const int iy = cellIdx / gridW;

            for (int dy = -neighborRange; dy <= neighborRange; ++dy) {
                int ny = iy + dy;
                if (ny < 0 || ny >= gridH) continue;
                int rowOffset = ny * gridW;
                for (int dx = -neighborRange; dx <= neighborRange; ++dx) {
                    int nx = ix + dx;
                    if (nx < 0 || nx >= gridW) continue;
                    int nCellIdx = rowOffset + nx;

                    int begin = cellOffsets[nCellIdx];
                    int end = cellOffsets[nCellIdx + 1];
                    for (int idx = begin; idx < end; ++idx) {
                        int j = sortedIndices[idx];
                        if (j == i) continue;

                        const Particle &pj = pData[j];

                        float dxp = pj.position.x - pix;
                        float dyp = pj.position.y - piy;
                        float dist2 = dxp * dxp + dyp * dyp;
                        if (dist2 < R2) {
                            totalForce += computeForce(pi, pj, R);
                        }
                    }
                }
            }

            outData[i] = updateParticle(pi, totalForce, dt);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}