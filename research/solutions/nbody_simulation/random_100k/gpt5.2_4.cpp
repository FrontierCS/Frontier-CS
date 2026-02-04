#include "world.h"
#include <omp.h>

#include <vector>
#include <cmath>
#include <algorithm>
#include <cfloat>
#include <cstdint>

class MySimulator : public Simulator {
private:
    struct Node {
        float cx, cy;
        float hs;
        int child[4];
        int head;   // head particle index for leaf
        int count;  // number of particles in leaf
        float mass;
        float comx, comy;
        Node() : cx(0), cy(0), hs(0), head(-1), count(0), mass(0), comx(0), comy(0) {
            child[0] = child[1] = child[2] = child[3] = -1;
        }
        Node(float _cx, float _cy, float _hs) : cx(_cx), cy(_cy), hs(_hs), head(-1), count(0), mass(0), comx(_cx), comy(_cy) {
            child[0] = child[1] = child[2] = child[3] = -1;
        }
        inline bool isLeaf() const { return child[0] == -1; }
    };

    int numThreads = 16;
    int maxDepth = 20;

    std::vector<Node> nodes;
    std::vector<int> nextIdx;

    const std::vector<Particle>* curParticles = nullptr;

    float theta = 0.40f;

    inline int quadrant(const Node& n, float x, float y) const {
        const int east = (x > n.cx) ? 1 : 0;
        const int north = (y > n.cy) ? 1 : 0;
        return (north << 1) | east;
    }

    inline void ensureChildren(int nodeIdx) {
        Node &n = nodes[nodeIdx];
        if (!n.isLeaf()) return;

        float hh = n.hs * 0.5f;
        if (hh <= 0.0f) hh = 1e-6f;

        for (int q = 0; q < 4; q++) {
            float ccx = n.cx + ((q & 1) ? hh : -hh);
            float ccy = n.cy + ((q & 2) ? hh : -hh);
            n.child[q] = (int)nodes.size();
            nodes.emplace_back(ccx, ccy, hh);
        }
        n.head = -1;
        n.count = 0;
    }

    void insertParticle(int nodeIdx, int pIdx, int depth) {
        Node &n = nodes[nodeIdx];

        if (n.isLeaf()) {
            if (n.count == 0) {
                n.head = pIdx;
                nextIdx[pIdx] = -1;
                n.count = 1;
                return;
            }

            if (depth >= maxDepth) {
                nextIdx[pIdx] = n.head;
                n.head = pIdx;
                n.count++;
                return;
            }

            const auto &P = (*curParticles);
            int first = n.head;
            const float fx = P[first].position.x;
            const float fy = P[first].position.y;
            const float px = P[pIdx].position.x;
            const float py = P[pIdx].position.y;

            if (fx == px && fy == py) {
                nextIdx[pIdx] = n.head;
                n.head = pIdx;
                n.count++;
                return;
            }

            int oldHead = n.head;
            ensureChildren(nodeIdx);

            int cur = oldHead;
            while (cur != -1) {
                int nxt = nextIdx[cur];
                nextIdx[cur] = -1;
                insertParticle(nodeIdx, cur, depth);
                cur = nxt;
            }
            insertParticle(nodeIdx, pIdx, depth);
            return;
        }

        const auto &P = (*curParticles);
        float x = P[pIdx].position.x;
        float y = P[pIdx].position.y;

        int q = quadrant(n, x, y);
        int c = n.child[q];
        if (c < 0) {
            // Should not happen, but guard
            ensureChildren(nodeIdx);
            c = n.child[q];
        }
        insertParticle(c, pIdx, depth + 1);
    }

    void computeMassCom(int nodeIdx) {
        Node &n = nodes[nodeIdx];
        if (n.isLeaf()) {
            float m = 0.0f, wx = 0.0f, wy = 0.0f;
            const auto &P = (*curParticles);
            for (int p = n.head; p != -1; p = nextIdx[p]) {
                float pm = P[p].mass;
                m += pm;
                wx += pm * P[p].position.x;
                wy += pm * P[p].position.y;
            }
            n.mass = m;
            if (m > 0.0f) {
                n.comx = wx / m;
                n.comy = wy / m;
            } else {
                n.comx = n.cx;
                n.comy = n.cy;
            }
            return;
        }

        float m = 0.0f, wx = 0.0f, wy = 0.0f;
        for (int k = 0; k < 4; k++) {
            int c = n.child[k];
            if (c >= 0) {
                computeMassCom(c);
                const Node &cn = nodes[c];
                m += cn.mass;
                wx += cn.mass * cn.comx;
                wy += cn.mass * cn.comy;
            }
        }
        n.mass = m;
        if (m > 0.0f) {
            n.comx = wx / m;
            n.comy = wy / m;
        } else {
            n.comx = n.cx;
            n.comy = n.cy;
        }
    }

    inline float minDist2ToAABB(float px, float py, const Node& n) const {
        float adx = std::fabs(px - n.cx);
        float ady = std::fabs(py - n.cy);
        float dx = adx - n.hs;
        float dy = ady - n.hs;
        if (dx < 0.0f) dx = 0.0f;
        if (dy < 0.0f) dy = 0.0f;
        return dx * dx + dy * dy;
    }

    inline float maxDist2ToAABB(float px, float py, const Node& n) const {
        float adx = std::fabs(px - n.cx) + n.hs;
        float ady = std::fabs(py - n.cy) + n.hs;
        return adx * adx + ady * ady;
    }

public:
    void init(int numParticles, StepParameters) override {
        int procs = omp_get_num_procs();
        numThreads = std::min(16, std::max(1, procs));
        omp_set_dynamic(0);
        omp_set_num_threads(numThreads);

        nextIdx.assign(numParticles, -1);
        nodes.clear();
        nodes.reserve((size_t)numParticles * 4u);
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = (int)particles.size();
        if ((int)newParticles.size() != n) newParticles.resize(n);
        if ((int)nextIdx.size() != n) nextIdx.assign(n, -1);
        else std::fill(nextIdx.begin(), nextIdx.end(), -1);

        curParticles = &particles;

        float minx = FLT_MAX, miny = FLT_MAX, maxx = -FLT_MAX, maxy = -FLT_MAX;
        #pragma omp parallel
        {
            float lminx = FLT_MAX, lminy = FLT_MAX, lmaxx = -FLT_MAX, lmaxy = -FLT_MAX;
            #pragma omp for nowait
            for (int i = 0; i < n; i++) {
                float x = particles[i].position.x;
                float y = particles[i].position.y;
                lminx = std::min(lminx, x);
                lminy = std::min(lminy, y);
                lmaxx = std::max(lmaxx, x);
                lmaxy = std::max(lmaxy, y);
            }
            #pragma omp critical
            {
                minx = std::min(minx, lminx);
                miny = std::min(miny, lminy);
                maxx = std::max(maxx, lmaxx);
                maxy = std::max(maxy, lmaxy);
            }
        }

        float cx = 0.5f * (minx + maxx);
        float cy = 0.5f * (miny + maxy);
        float spanx = maxx - minx;
        float spany = maxy - miny;
        float half = 0.5f * std::max(spanx, spany);
        half += 1e-3f;
        half *= 1.001f;

        nodes.clear();
        nodes.emplace_back(cx, cy, half);

        for (int i = 0; i < n; i++) {
            insertParticle(0, i, 0);
        }
        computeMassCom(0);

        const float r = params.cullRadius;
        const float r2 = r * r;
        const float theta2 = theta * theta;

        #pragma omp parallel for schedule(guided, 128)
        for (int i = 0; i < n; i++) {
            const Particle &pi = particles[i];
            const float px = pi.position.x;
            const float py = pi.position.y;

            Vec2 force(0.0f, 0.0f);

            int stack[96];
            int sp = 0;
            stack[sp++] = 0;

            while (sp) {
                int idx = stack[--sp];
                const Node &node = nodes[idx];
                if (node.mass == 0.0f) continue;

                if (minDist2ToAABB(px, py, node) > r2) continue;

                if (node.isLeaf()) {
                    for (int p = node.head; p != -1; p = nextIdx[p]) {
                        if (p == i) continue;
                        float dx = particles[p].position.x - px;
                        float dy = particles[p].position.y - py;
                        float d2 = dx * dx + dy * dy;
                        if (d2 < r2 && d2 > 1e-12f) {
                            force += computeForce(pi, particles[p], r);
                        }
                    }
                } else {
                    float adx = std::fabs(px - node.cx);
                    float ady = std::fabs(py - node.cy);
                    bool contains = (adx <= node.hs && ady <= node.hs);

                    bool didApprox = false;
                    if (!contains) {
                        if (maxDist2ToAABB(px, py, node) <= r2) {
                            float dx = node.comx - px;
                            float dy = node.comy - py;
                            float d2 = dx * dx + dy * dy;
                            if (d2 > 1e-12f) {
                                float s = node.hs * 2.0f;
                                if ((s * s) <= theta2 * d2) {
                                    Particle pseudo;
                                    pseudo.id = -1;
                                    pseudo.mass = node.mass;
                                    pseudo.position = Vec2{node.comx, node.comy};
                                    pseudo.velocity = Vec2{0.0f, 0.0f};
                                    force += computeForce(pi, pseudo, r);
                                    didApprox = true;
                                }
                            }
                        }
                    }

                    if (!didApprox) {
                        int c0 = node.child[0], c1 = node.child[1], c2 = node.child[2], c3 = node.child[3];
                        if (c0 >= 0) stack[sp++] = c0;
                        if (c1 >= 0) stack[sp++] = c1;
                        if (c2 >= 0) stack[sp++] = c2;
                        if (c3 >= 0) stack[sp++] = c3;
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