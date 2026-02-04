#include "world.h"
#include <omp.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

class MySimulator : public Simulator {
private:
    struct Node {
        float cx = 0.0f, cy = 0.0f, half = 0.0f; // square AABB: [cx-half,cx+half] x [cy-half,cy+half]
        int child[4] = {-1, -1, -1, -1};         // 0:LB, 1:RB, 2:LT, 3:RT
        int particle = -1;                       // >=0 single particle index, -1 empty/internal, -2 bucket
        int bucketHead = -1;
        int bucketCount = 0;

        int count = 0;      // particles in subtree
        float mass = 0.0f;  // total mass
        float comx = 0.0f;  // center of mass
        float comy = 0.0f;

        inline bool isLeaf() const { return child[0] == -1; }
        inline bool isInternal() const { return child[0] != -1; }
    };

    int numThreads = 16;

    std::vector<Node> nodes;

    std::vector<int> bucketParticle;
    std::vector<int> bucketNext;

    std::vector<int> traversalOrder;

    int maxDepth = 24;
    float minHalf = 1e-5f;

    float theta = 0.30f;
    float theta2 = theta * theta;
    float minApproxDist2 = 0.04f; // (0.2)^2

    inline int newNode(float cx, float cy, float half) {
        Node n;
        n.cx = cx;
        n.cy = cy;
        n.half = half;
        nodes.push_back(n);
        return (int)nodes.size() - 1;
    }

    inline int quadrant(const Vec2 &p, const Node &n) const {
        int q = 0;
        if (p.x >= n.cx) q |= 1;
        if (p.y >= n.cy) q |= 2;
        return q;
    }

    inline void addToBucket(Node &n, int pIdx) {
        int e = (int)bucketParticle.size();
        bucketParticle.push_back(pIdx);
        bucketNext.push_back(n.bucketHead);
        n.bucketHead = e;
        n.bucketCount++;
        n.particle = -2;
    }

    void createChildren(int idx) {
        Node &n = nodes[idx];
        float h2 = n.half * 0.5f;
        for (int q = 0; q < 4; q++) {
            float ccx = n.cx + ((q & 1) ? h2 : -h2);
            float ccy = n.cy + ((q & 2) ? h2 : -h2);
            n.child[q] = newNode(ccx, ccy, h2);
        }
    }

    void insertParticle(int nodeIdx, int pIdx, int depth, const std::vector<Particle> &particles) {
        Node &n = nodes[nodeIdx];

        if (n.isLeaf()) {
            if (n.particle == -1 && n.bucketCount == 0) {
                n.particle = pIdx;
                return;
            }

            if (n.particle >= 0) {
                int old = n.particle;

                if (depth >= maxDepth || n.half <= minHalf) {
                    n.particle = -2;
                    n.bucketHead = -1;
                    n.bucketCount = 0;
                    addToBucket(n, old);
                    addToBucket(n, pIdx);
                    return;
                }

                n.particle = -1;
                createChildren(nodeIdx);

                int qOld = quadrant(particles[old].position, n);
                int qNew = quadrant(particles[pIdx].position, n);

                insertParticle(n.child[qOld], old, depth + 1, particles);
                insertParticle(n.child[qNew], pIdx, depth + 1, particles);
                return;
            }

            if (n.particle == -2) {
                addToBucket(n, pIdx);
                return;
            }

            // Should not reach here
            n.particle = pIdx;
            return;
        } else {
            int q = quadrant(particles[pIdx].position, n);
            insertParticle(n.child[q], pIdx, depth + 1, particles);
        }
    }

    void buildTree(const std::vector<Particle> &particles) {
        const int N = (int)particles.size();
        nodes.clear();
        bucketParticle.clear();
        bucketNext.clear();
        traversalOrder.clear();

        if (N == 0) return;

        nodes.reserve((size_t)4 * (size_t)N + 1024);
        bucketParticle.reserve((size_t)N / 8 + 1024);
        bucketNext.reserve((size_t)N / 8 + 1024);

        float minx = particles[0].position.x, maxx = minx;
        float miny = particles[0].position.y, maxy = miny;
        for (int i = 1; i < N; i++) {
            float x = particles[i].position.x;
            float y = particles[i].position.y;
            minx = std::min(minx, x);
            maxx = std::max(maxx, x);
            miny = std::min(miny, y);
            maxy = std::max(maxy, y);
        }

        float cx = 0.5f * (minx + maxx);
        float cy = 0.5f * (miny + maxy);
        float size = std::max(maxx - minx, maxy - miny);
        if (size < 1e-3f) size = 1e-3f;
        float half = 0.5f * size + 1e-3f;

        newNode(cx, cy, half);

        for (int i = 0; i < N; i++) insertParticle(0, i, 0, particles);

        traversalOrder.reserve(nodes.size());
        std::vector<int> st;
        st.reserve(nodes.size());
        st.push_back(0);
        while (!st.empty()) {
            int idx = st.back();
            st.pop_back();
            traversalOrder.push_back(idx);
            const Node &n = nodes[idx];
            if (n.isInternal()) {
                // push all children
                st.push_back(n.child[0]);
                st.push_back(n.child[1]);
                st.push_back(n.child[2]);
                st.push_back(n.child[3]);
            }
        }

        for (int k = (int)traversalOrder.size() - 1; k >= 0; k--) {
            int idx = traversalOrder[k];
            Node &n = nodes[idx];

            if (n.isLeaf()) {
                if (n.particle >= 0) {
                    const Particle &p = particles[n.particle];
                    n.count = 1;
                    n.mass = p.mass;
                    n.comx = p.position.x;
                    n.comy = p.position.y;
                } else if (n.particle == -2) {
                    double m = 0.0, sx = 0.0, sy = 0.0;
                    int e = n.bucketHead;
                    int c = 0;
                    while (e != -1) {
                        int pi = bucketParticle[e];
                        const Particle &p = particles[pi];
                        double pm = (double)p.mass;
                        m += pm;
                        sx += pm * (double)p.position.x;
                        sy += pm * (double)p.position.y;
                        c++;
                        e = bucketNext[e];
                    }
                    n.count = c;
                    if (m > 0.0) {
                        n.mass = (float)m;
                        n.comx = (float)(sx / m);
                        n.comy = (float)(sy / m);
                    } else {
                        n.mass = 0.0f;
                        n.comx = n.comy = 0.0f;
                    }
                } else {
                    n.count = 0;
                    n.mass = 0.0f;
                    n.comx = n.comy = 0.0f;
                }
            } else {
                double m = 0.0, sx = 0.0, sy = 0.0;
                int cnt = 0;
                for (int q = 0; q < 4; q++) {
                    const Node &c = nodes[n.child[q]];
                    if (c.count == 0) continue;
                    double cm = (double)c.mass;
                    m += cm;
                    sx += cm * (double)c.comx;
                    sy += cm * (double)c.comy;
                    cnt += c.count;
                }
                n.count = cnt;
                if (m > 0.0) {
                    n.mass = (float)m;
                    n.comx = (float)(sx / m);
                    n.comy = (float)(sy / m);
                } else {
                    n.mass = 0.0f;
                    n.comx = n.comy = 0.0f;
                }
            }
        }
    }

public:
    void init(int numParticles, StepParameters params) override {
        (void)numParticles;
        (void)params;
        int maxT = omp_get_max_threads();
        numThreads = std::min(16, maxT);
        if (numThreads < 1) numThreads = 1;
        omp_set_num_threads(numThreads);

        nodes.clear();
        bucketParticle.clear();
        bucketNext.clear();
        traversalOrder.clear();
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int N = (int)particles.size();
        if ((int)newParticles.size() != N) newParticles.resize(N);
        if (N == 0) return;

        buildTree(particles);

        const float r = params.cullRadius;
        const float r2 = r * r;
        const float dt = params.deltaTime;

        #pragma omp parallel
        {
            std::vector<int> stack;
            stack.reserve(512);

            #pragma omp for schedule(guided, 64)
            for (int i = 0; i < N; i++) {
                const Particle &pi = particles[i];
                const float px = pi.position.x;
                const float py = pi.position.y;

                float fx = 0.0f, fy = 0.0f;

                stack.clear();
                stack.push_back(0);

                while (!stack.empty()) {
                    int ni = stack.back();
                    stack.pop_back();

                    const Node &n = nodes[ni];
                    if (n.count == 0) continue;

                    float adx = std::fabs(px - n.cx);
                    float ady = std::fabs(py - n.cy);

                    float dx = adx - n.half;
                    float dy = ady - n.half;
                    if (dx < 0.0f) dx = 0.0f;
                    if (dy < 0.0f) dy = 0.0f;
                    if (dx * dx + dy * dy > r2) continue;

                    if (n.isLeaf()) {
                        if (n.particle >= 0) {
                            int pj = n.particle;
                            if (pj != i) {
                                Vec2 f = computeForce(pi, particles[pj], r);
                                fx += f.x;
                                fy += f.y;
                            }
                        } else if (n.particle == -2) {
                            int e = n.bucketHead;
                            while (e != -1) {
                                int pj = bucketParticle[e];
                                if (pj != i) {
                                    Vec2 f = computeForce(pi, particles[pj], r);
                                    fx += f.x;
                                    fy += f.y;
                                }
                                e = bucketNext[e];
                            }
                        }
                        continue;
                    }

                    bool contains = (adx <= n.half) && (ady <= n.half);

                    float dxmax = adx + n.half;
                    float dymax = ady + n.half;
                    bool fullyInside = (dxmax * dxmax + dymax * dymax) <= r2;

                    if (fullyInside && !contains) {
                        float dcomx = n.comx - px;
                        float dcomy = n.comy - py;
                        float d2 = dcomx * dcomx + dcomy * dcomy;
                        if (d2 > minApproxDist2) {
                            float s = n.half * 2.0f;
                            if ((s * s) < (theta2 * d2)) {
                                Particle agg;
                                agg.id = -1;
                                agg.mass = n.mass;
                                agg.position = Vec2(n.comx, n.comy);
                                agg.velocity = Vec2(0.0f, 0.0f);

                                Vec2 f = computeForce(pi, agg, r);
                                fx += f.x;
                                fy += f.y;
                                continue;
                            }
                        }
                    }

                    stack.push_back(n.child[0]);
                    stack.push_back(n.child[1]);
                    stack.push_back(n.child[2]);
                    stack.push_back(n.child[3]);
                }

                newParticles[i] = updateParticle(pi, Vec2(fx, fy), dt);
            }
        }
    }
};

Simulator *createSimulator() {
    return new MySimulator();
}