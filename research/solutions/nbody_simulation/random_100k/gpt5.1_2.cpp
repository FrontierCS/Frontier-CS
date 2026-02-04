#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <limits>
#include <cmath>

struct KDNode {
    float minX, maxX, minY, maxY;
    int start, end;
    int left, right;
};

class MySimulator : public Simulator {
private:
    int numThreads = 0;
    int leafSize = 16;
    std::vector<int> indices;
    std::vector<KDNode> nodes;
    const Particle* points = nullptr;
    float radius = 0.0f;
    float radius2 = 0.0f;
    float deltaTime = 0.0f;
    int root = -1;

    inline void computeBounding(int start, int end,
                                float &minX, float &maxX,
                                float &minY, float &maxY) {
        minX = std::numeric_limits<float>::infinity();
        minY = std::numeric_limits<float>::infinity();
        maxX = -std::numeric_limits<float>::infinity();
        maxY = -std::numeric_limits<float>::infinity();

        for (int i = start; i < end; ++i) {
            const Particle &p = points[ indices[i] ];
            float x = p.position.x;
            float y = p.position.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        if (start == end) {
            minX = maxX = minY = maxY = 0.0f;
        }
    }

    int buildNode(int start, int end) {
        if (start >= end) return -1;

        int nodeIdx = (int)nodes.size();
        nodes.emplace_back();
        KDNode &node = nodes.back();

        node.start = start;
        node.end = end;

        computeBounding(start, end, node.minX, node.maxX, node.minY, node.maxY);

        int count = end - start;
        if (count <= leafSize) {
            node.left = -1;
            node.right = -1;
        } else {
            float rangeX = node.maxX - node.minX;
            float rangeY = node.maxY - node.minY;
            int axis = (rangeX > rangeY) ? 0 : 1;

            int mid = start + count / 2;
            auto beginIt = indices.begin() + start;
            auto midIt   = indices.begin() + mid;
            auto endIt   = indices.begin() + end;

            const Particle* localPoints = points;
            if (axis == 0) {
                std::nth_element(beginIt, midIt, endIt,
                    [localPoints](int a, int b) {
                        return localPoints[a].position.x < localPoints[b].position.x;
                    });
            } else {
                std::nth_element(beginIt, midIt, endIt,
                    [localPoints](int a, int b) {
                        return localPoints[a].position.y < localPoints[b].position.y;
                    });
            }

            node.left  = buildNode(start, mid);
            node.right = buildNode(mid, end);
        }

        return nodeIdx;
    }

    inline bool bboxIntersectsCircle(const KDNode &node, const Vec2 &pos) const {
        float dx = 0.0f;
        if (pos.x < node.minX) dx = node.minX - pos.x;
        else if (pos.x > node.maxX) dx = pos.x - node.maxX;

        float dy = 0.0f;
        if (pos.y < node.minY) dy = node.minY - pos.y;
        else if (pos.y > node.maxY) dy = pos.y - node.maxY;

        return dx * dx + dy * dy <= radius2;
    }

    void rangeSearch(int nodeIdx, int targetIndex,
                     const Particle &target, Vec2 &force) const {
        const KDNode &node = nodes[nodeIdx];
        if (!bboxIntersectsCircle(node, target.position))
            return;

        if (node.left == -1) {
            for (int i = node.start; i < node.end; ++i) {
                int j = indices[i];
                if (j == targetIndex) continue;

                const Particle &pj = points[j];
                float dx = pj.position.x - target.position.x;
                float dy = pj.position.y - target.position.y;
                float dist2 = dx * dx + dy * dy;
                if (dist2 <= radius2) {
                    force += computeForce(target, pj, radius);
                }
            }
        } else {
            rangeSearch(node.left,  targetIndex, target, force);
            rangeSearch(node.right, targetIndex, target, force);
        }
    }

public:
    MySimulator() {
        numThreads = 0;
        leafSize = 16;
    }

    void init(int numParticles, StepParameters params) override {
        (void)params;
        numThreads = omp_get_max_threads();
        if (numThreads <= 0) numThreads = 1;
        omp_set_num_threads(numThreads);

        if (numParticles > 0) {
            indices.resize(numParticles);
            nodes.reserve(numParticles * 2);
        }
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        int n = (int)particles.size();
        if (n == 0) return;

        if ((int)indices.size() < n)
            indices.resize(n);

        if ((int)nodes.capacity() < 2 * n)
            nodes.reserve(2 * n);

        points = particles.data();
        radius = params.cullRadius;
        radius2 = radius * radius;
        deltaTime = params.deltaTime;

        for (int i = 0; i < n; ++i)
            indices[i] = i;

        nodes.clear();
        root = buildNode(0, n);

        #pragma omp parallel for schedule(static)
        for (int i = 0; i < n; ++i) {
            const Particle &pi = particles[i];
            Vec2 force(0.0f, 0.0f);
            rangeSearch(root, i, pi, force);
            newParticles[i] = updateParticle(pi, force, deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}