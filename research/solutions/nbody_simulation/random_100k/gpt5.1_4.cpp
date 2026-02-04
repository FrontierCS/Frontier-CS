#include "world.h"
#include <omp.h>
#include <vector>
#include <algorithm>
#include <cmath>

class MySimulator : public Simulator {
private:
    struct Node {
        float minX, maxX, minY, maxY;
        float cx, cy;
        float mass;
        float size;      // max(maxX-minX, maxY-minY)
        int child[4];    // indices of children, -1 if none
        int body;        // index of first body if leaf, -1 otherwise
        int bodyCount;   // number of bodies in this leaf (for maxDepth leaves)
        bool isLeaf;
    };

    std::vector<Node> nodes;
    std::vector<int> nextBody;  // linked list for bodies in multi-body leaves

    int maxDepth;
    float theta;
    float theta2;
    int numThreads;

    int createNode(float minX, float maxX, float minY, float maxY) {
        Node node;
        node.minX = minX;
        node.maxX = maxX;
        node.minY = minY;
        node.maxY = maxY;
        node.cx = 0.0f;
        node.cy = 0.0f;
        node.mass = 0.0f;
        node.size = std::max(maxX - minX, maxY - minY);
        node.body = -1;
        node.bodyCount = 0;
        node.isLeaf = true;
        node.child[0] = node.child[1] = node.child[2] = node.child[3] = -1;
        nodes.push_back(node);
        return static_cast<int>(nodes.size()) - 1;
    }

    void subdivideNode(int nodeIdx) {
        Node &node = nodes[nodeIdx];
        float midX = 0.5f * (node.minX + node.maxX);
        float midY = 0.5f * (node.minY + node.maxY);
        // SW
        node.child[0] = createNode(node.minX, midX, node.minY, midY);
        // SE
        node.child[1] = createNode(midX, node.maxX, node.minY, midY);
        // NW
        node.child[2] = createNode(node.minX, midX, midY, node.maxY);
        // NE
        node.child[3] = createNode(midX, node.maxX, midY, node.maxY);
        node.isLeaf = false;
    }

    int getQuadrant(const Node &node, const Particle &p) const {
        float midX = 0.5f * (node.minX + node.maxX);
        float midY = 0.5f * (node.minY + node.maxY);
        int quad = 0;
        if (p.position.y >= midY) quad += 2; // north
        if (p.position.x >= midX) quad += 1; // east
        return quad;
    }

    void insertBodyToChild(int nodeIdx, int bodyIdx, int depth,
                           const std::vector<Particle> &particles) {
        Node &node = nodes[nodeIdx];
        int quad = getQuadrant(node, particles[bodyIdx]);
        int childIdx = node.child[quad];
        if (childIdx == -1) {
            float midX = 0.5f * (node.minX + node.maxX);
            float midY = 0.5f * (node.minY + node.maxY);
            float cminX, cmaxX, cminY, cmaxY;
            if (quad & 1) { // east
                cminX = midX;
                cmaxX = node.maxX;
            } else {        // west
                cminX = node.minX;
                cmaxX = midX;
            }
            if (quad & 2) { // north
                cminY = midY;
                cmaxY = node.maxY;
            } else {        // south
                cminY = node.minY;
                cmaxY = midY;
            }
            childIdx = createNode(cminX, cmaxX, cminY, cmaxY);
            node.child[quad] = childIdx;
        }
        insertBody(childIdx, bodyIdx, depth, particles);
    }

    void insertBody(int nodeIdx, int bodyIdx, int depth,
                    const std::vector<Particle> &particles) {
        Node &node = nodes[nodeIdx];
        if (node.isLeaf) {
            if (node.body == -1) {
                node.body = bodyIdx;
                node.bodyCount = 1;
                nextBody[bodyIdx] = -1;
            } else if (depth >= maxDepth) {
                // Multi-body leaf at maximum depth
                nextBody[bodyIdx] = node.body;
                node.body = bodyIdx;
                node.bodyCount++;
            } else {
                // Subdivide leaf and reinsert existing bodies
                subdivideNode(nodeIdx);
                int existing = node.body;
                node.body = -1;
                node.bodyCount = 0;
                while (existing != -1) {
                    int next = nextBody[existing];
                    insertBodyToChild(nodeIdx, existing, depth + 1, particles);
                    existing = next;
                }
                // Insert new body
                insertBodyToChild(nodeIdx, bodyIdx, depth + 1, particles);
            }
        } else {
            insertBodyToChild(nodeIdx, bodyIdx, depth + 1, particles);
        }
    }

    void computeMass(int nodeIdx, const std::vector<Particle> &particles) {
        Node &node = nodes[nodeIdx];
        if (node.isLeaf) {
            if (node.body == -1) {
                node.mass = 0.0f;
                node.cx = node.cy = 0.0f;
                return;
            }
            float mSum = 0.0f;
            float xSum = 0.0f;
            float ySum = 0.0f;
            int idx = node.body;
            while (idx != -1) {
                float m = particles[idx].mass;
                mSum += m;
                xSum += particles[idx].position.x * m;
                ySum += particles[idx].position.y * m;
                idx = nextBody[idx];
            }
            node.mass = mSum;
            if (mSum > 0.0f) {
                float invM = 1.0f / mSum;
                node.cx = xSum * invM;
                node.cy = ySum * invM;
            } else {
                node.cx = node.cy = 0.0f;
            }
        } else {
            float mSum = 0.0f;
            float xSum = 0.0f;
            float ySum = 0.0f;
            for (int k = 0; k < 4; ++k) {
                int c = node.child[k];
                if (c != -1) {
                    computeMass(c, particles);
                    float cm = nodes[c].mass;
                    if (cm > 0.0f) {
                        mSum += cm;
                        xSum += nodes[c].cx * cm;
                        ySum += nodes[c].cy * cm;
                    }
                }
            }
            node.mass = mSum;
            if (mSum > 0.0f) {
                float invM = 1.0f / mSum;
                node.cx = xSum * invM;
                node.cy = ySum * invM;
            } else {
                node.cx = node.cy = 0.0f;
            }
        }
    }

    inline Vec2 computeAggregateForce(const Particle &target, float mass,
                                      float posX, float posY,
                                      float cullRadius) const {
        Vec2 dir;
        dir.x = posX - target.position.x;
        dir.y = posY - target.position.y;
        float dist = dir.length();
        if (dist < 1e-3f)
            return Vec2(0.0f, 0.0f);
        dir *= (1.0f / dist);
        if (dist > cullRadius)
            return Vec2(0.0f, 0.0f);
        if (dist < 1e-1f)
            dist = 1e-1f;
        const float G = 0.01f;
        Vec2 force = dir * target.mass * mass * (G / (dist * dist));
        if (dist > cullRadius * 0.75f) {
            float decay =
                1.0f - (dist - cullRadius * 0.75f) / (cullRadius * 0.25f);
            force *= decay;
        }
        return force;
    }

    void traverseNode(int nodeIdx, int targetIdx,
                      const std::vector<Particle> &particles,
                      Vec2 &forceAcc, float cullRadius,
                      float cullRadius2) const {
        const Node &node = nodes[nodeIdx];
        if (node.mass <= 0.0f)
            return;

        const Particle &target = particles[targetIdx];
        float tx = target.position.x;
        float ty = target.position.y;

        // Minimum distance squared from target to node's AABB
        float dx = 0.0f;
        if (tx < node.minX)
            dx = node.minX - tx;
        else if (tx > node.maxX)
            dx = tx - node.maxX;

        float dy = 0.0f;
        if (ty < node.minY)
            dy = node.minY - ty;
        else if (ty > node.maxY)
            dy = ty - node.maxY;

        float minDist2 = dx * dx + dy * dy;
        if (minDist2 > cullRadius2)
            return;

        if (node.isLeaf) {
            int b = node.body;
            while (b != -1) {
                if (b != targetIdx) {
                    forceAcc += computeForce(target, particles[b], cullRadius);
                }
                b = nextBody[b];
            }
            return;
        }

        // Distance squared from target to node's center of mass
        float dxcm = node.cx - tx;
        float dycm = node.cy - ty;
        float dist2cm = dxcm * dxcm + dycm * dycm;

        // Maximum distance squared from target to node's corners
        float dxmax = std::max(std::fabs(tx - node.minX),
                               std::fabs(tx - node.maxX));
        float dymax = std::max(std::fabs(ty - node.minY),
                               std::fabs(ty - node.maxY));
        float maxDist2 = dxmax * dxmax + dymax * dymax;
        bool fullyInside = (maxDist2 <= cullRadius2);

        bool usedApprox = false;
        if (fullyInside && dist2cm > 0.0f) {
            float s = node.size;
            // Barnes-Hut opening criterion: s / sqrt(dist2) < theta
            if (s * s < theta2 * dist2cm) {
                Vec2 f =
                    computeAggregateForce(target, node.mass, node.cx, node.cy,
                                          cullRadius);
                forceAcc += f;
                usedApprox = true;
            }
        }

        if (!usedApprox) {
            for (int k = 0; k < 4; ++k) {
                int c = node.child[k];
                if (c != -1) {
                    traverseNode(c, targetIdx, particles, forceAcc,
                                 cullRadius, cullRadius2);
                }
            }
        }
    }

public:
    MySimulator() {
        maxDepth = 20;
        theta = 0.5f;
        theta2 = theta * theta;
        numThreads = 0;
    }

    void init(int numParticles, StepParameters params) override {
        numThreads = omp_get_max_threads();
        if (numThreads <= 0)
            numThreads = 1;
        omp_set_num_threads(numThreads);
        nodes.reserve(numParticles * 4);
        nextBody.assign(numParticles, -1);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        int N = static_cast<int>(particles.size());
        if (N == 0)
            return;

        if (static_cast<int>(nextBody.size()) < N) {
            nextBody.assign(N, -1);
        } else {
            std::fill(nextBody.begin(), nextBody.begin() + N, -1);
        }

        // Compute bounding box of all particles
        float minX = particles[0].position.x;
        float maxX = particles[0].position.x;
        float minY = particles[0].position.y;
        float maxY = particles[0].position.y;

        for (int i = 1; i < N; ++i) {
            float x = particles[i].position.x;
            float y = particles[i].position.y;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        float padding = 1e-3f;
        if (maxX - minX < 1e-3f) {
            maxX = minX + 0.5f;
            minX = minX - 0.5f;
        } else {
            minX -= padding;
            maxX += padding;
        }
        if (maxY - minY < 1e-3f) {
            maxY = minY + 0.5f;
            minY = minY - 0.5f;
        } else {
            minY -= padding;
            maxY += padding;
        }

        nodes.clear();
        nodes.reserve(N * 4);
        int rootIdx = createNode(minX, maxX, minY, maxY);

        for (int i = 0; i < N; ++i) {
            insertBody(rootIdx, i, 0, particles);
        }

        computeMass(rootIdx, particles);

        float cullRadius = params.cullRadius;
        float cullRadius2 = cullRadius * cullRadius;

        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N; ++i) {
            Vec2 force(0.0f, 0.0f);
            traverseNode(rootIdx, i, particles, force, cullRadius, cullRadius2);
            newParticles[i] =
                updateParticle(particles[i], force, params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}