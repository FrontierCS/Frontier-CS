#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <numeric>
#include <limits>
#include <cmath>

class MySimulator : public Simulator {
private:
    int numThreads = 16;

    struct QuadNode {
        Vec2 minPos, maxPos;
        std::vector<int> particleIndices;
        QuadNode* children[4] = {nullptr, nullptr, nullptr, nullptr};

        QuadNode(Vec2 mn, Vec2 mx) : minPos(mn), maxPos(mx) {}
        ~QuadNode() {
            for (int i = 0; i < 4; ++i) {
                delete children[i];
            }
        }
    };

    void build(QuadNode* node, const std::vector<Particle>& particles, std::vector<int>& indices, float minSize) {
        if (indices.empty()) return;

        float width = node->maxPos.x - node->minPos.x;
        float height = node->maxPos.y - node->minPos.y;
        if (width <= minSize || height <= minSize || indices.size() <= 4) {
            node->particleIndices = std::move(indices);
            return;
        }

        float midX = (node->minPos.x + node->maxPos.x) * 0.5f;
        float midY = (node->minPos.y + node->maxPos.y) * 0.5f;

        std::vector<int> childIndices[4];
        for (int idx : indices) {
            const Vec2& pos = particles[idx].position;
            int q;
            if (pos.x <= midX) {
                q = (pos.y <= midY) ? 0 : 1;
            } else {
                q = (pos.y <= midY) ? 2 : 3;
            }
            childIndices[q].push_back(idx);
        }

        Vec2 cmin[4] = {
            {node->minPos.x, node->minPos.y},
            {node->minPos.x, midY},
            {midX, node->minPos.y},
            {midX, midY}
        };
        Vec2 cmax[4] = {
            {midX, midY},
            {midX, node->maxPos.y},
            {node->maxPos.x, midY},
            {node->maxPos.x, node->maxPos.y}
        };

        for (int q = 0; q < 4; ++q) {
            node->children[q] = new QuadNode(cmin[q], cmax[q]);
            if (!childIndices[q].empty()) {
                build(node->children[q], particles, childIndices[q], minSize);
            } else {
                delete node->children[q];
                node->children[q] = nullptr;
            }
        }
    }

    void accumulateForce(QuadNode* node, const Particle& target, float cullRadius, Vec2& totalForce, const std::vector<Particle>& particles) {
        if (!node) return;

        Vec2 qpos = target.position;
        float r2 = cullRadius * cullRadius;

        Vec2 bmin = node->minPos;
        Vec2 bmax = node->maxPos;

        float dx = std::max(bmin.x - qpos.x, std::max(0.0f, qpos.x - bmax.x));
        float dy = std::max(bmin.y - qpos.y, std::max(0.0f, qpos.y - bmax.y));
        float minD2 = dx * dx + dy * dy;
        if (minD2 > r2) return;

        if (!node->particleIndices.empty()) {
            for (int j : node->particleIndices) {
                totalForce += computeForce(target, particles[j], cullRadius);
            }
        } else {
            for (int q = 0; q < 4; ++q) {
                accumulateForce(node->children[q], target, cullRadius, totalForce, particles);
            }
        }
    }

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
    }

    void simulateStep(std::vector<Particle>& particles,
                      std::vector<Particle>& newParticles,
                      StepParameters params) override {
        size_t N = particles.size();
        if (N == 0) return;

        float INF = std::numeric_limits<float>::infinity();
        float minX = INF, minY = INF, maxX = -INF, maxY = -INF;
        for (const auto& p : particles) {
            minX = std::min(minX, p.position.x);
            minY = std::min(minY, p.position.y);
            maxX = std::max(maxX, p.position.x);
            maxY = std::max(maxY, p.position.y);
        }

        if (minX >= maxX || minY >= maxY) {
            newParticles = particles;
            return;
        }

        QuadNode* root = new QuadNode({minX, minY}, {maxX, maxY});
        std::vector<int> indices(N);
        std::iota(indices.begin(), indices.end(), 0);
        build(root, particles, indices, 1e-3f);

        #pragma omp parallel for schedule(dynamic, 1)
        for (size_t i = 0; i < N; ++i) {
            const auto& pi = particles[i];
            Vec2 force = {0.0f, 0.0f};
            accumulateForce(root, pi, params.cullRadius, force, particles);
            newParticles[i] = updateParticle(pi, force, params.deltaTime);
        }

        delete root;
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}