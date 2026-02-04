#include "world.h"
#include <omp.h>

#include <vector>
#include <cmath>
#include <cfloat>
#include <algorithm>
#include <cstdint>

class MySimulator : public Simulator {
private:
    struct Node {
        float cx = 0.0f, cy = 0.0f, half = 0.0f;
        float mass = 0.0f, comx = 0.0f, comy = 0.0f;
        int child[4] = {-1, -1, -1, -1}; // 0: (-x,-y), 1: (+x,-y), 2: (-x,+y), 3: (+x,+y)
        int head = -1; // leaf: head of particle linked list, -1 empty; internal: -2
    };

    int numThreads = 16;

    std::vector<float> px, py, pm;
    std::vector<int> nextInLeaf;
    std::vector<Node> nodes;

    float theta = 0.4f;
    float minHalf = 1e-3f;
    int maxDepth = 24;

    inline void makeChildren(int idx) {
        Node &n = nodes[idx];
        float h = n.half * 0.5f;
        int base = (int)nodes.size();
        nodes.resize(base + 4);
        for (int q = 0; q < 4; q++) {
            Node c;
            c.half = h;
            c.cx = n.cx + ((q & 1) ? h : -h);
            c.cy = n.cy + ((q & 2) ? h : -h);
            c.comx = c.cx;
            c.comy = c.cy;
            c.mass = 0.0f;
            c.head = -1;
            c.child[0] = c.child[1] = c.child[2] = c.child[3] = -1;
            nodes[base + q] = c;
            n.child[q] = base + q;
        }
    }

    inline int quadrant(int nodeIdx, int pIdx) const {
        const Node &n = nodes[nodeIdx];
        int q = (px[pIdx] >= n.cx) ? 1 : 0;
        if (py[pIdx] >= n.cy) q |= 2;
        return q;
    }

    void insertParticle(int nodeIdx, int pIdx, int depth) {
        Node &n = nodes[nodeIdx];
        if (n.head != -2) { // leaf
            if (n.head == -1) {
                n.head = pIdx;
                nextInLeaf[pIdx] = -1;
                return;
            }
            if (n.half <= minHalf || depth >= maxDepth) {
                nextInLeaf[pIdx] = n.head;
                n.head = pIdx;
                return;
            }

            int oldHead = n.head;
            n.head = -2;
            makeChildren(nodeIdx);

            int q = oldHead;
            while (q != -1) {
                int nq = nextInLeaf[q];
                nextInLeaf[q] = -1;
                int quad = quadrant(nodeIdx, q);
                insertParticle(n.child[quad], q, depth + 1);
                q = nq;
            }

            nextInLeaf[pIdx] = -1;
            int quad = quadrant(nodeIdx, pIdx);
            insertParticle(n.child[quad], pIdx, depth + 1);
            return;
        }

        int quad = quadrant(nodeIdx, pIdx);
        insertParticle(n.child[quad], pIdx, depth + 1);
    }

    void computeMassCOM() {
        std::vector<int> order;
        order.reserve(nodes.size());
        std::vector<int> st;
        st.reserve(256);
        st.push_back(0);
        while (!st.empty()) {
            int idx = st.back();
            st.pop_back();
            order.push_back(idx);
            const Node &n = nodes[idx];
            if (n.head == -2) {
                for (int k = 0; k < 4; k++) {
                    int c = n.child[k];
                    if (c != -1) st.push_back(c);
                }
            }
        }

        for (int oi = (int)order.size() - 1; oi >= 0; --oi) {
            int idx = order[oi];
            Node &n = nodes[idx];
            if (n.head != -2) {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int p = n.head; p != -1; p = nextInLeaf[p]) {
                    float mpv = pm[p];
                    m += mpv;
                    sx += mpv * px[p];
                    sy += mpv * py[p];
                }
                n.mass = m;
                if (m > 0.0f) {
                    float inv = 1.0f / m;
                    n.comx = sx * inv;
                    n.comy = sy * inv;
                } else {
                    n.comx = n.cx;
                    n.comy = n.cy;
                }
            } else {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int k = 0; k < 4; k++) {
                    int c = n.child[k];
                    if (c == -1) continue;
                    const Node &ch = nodes[c];
                    float cm = ch.mass;
                    m += cm;
                    sx += cm * ch.comx;
                    sy += cm * ch.comy;
                }
                n.mass = m;
                if (m > 0.0f) {
                    float inv = 1.0f / m;
                    n.comx = sx * inv;
                    n.comy = sy * inv;
                } else {
                    n.comx = n.cx;
                    n.comy = n.cy;
                }
            }
        }
    }

public:
    void init(int numParticles, StepParameters params) override {
        (void)params;
        omp_set_dynamic(0);
        int maxT = omp_get_max_threads();
        numThreads = std::min(16, maxT > 0 ? maxT : 16);
        omp_set_num_threads(numThreads);

        px.resize(numParticles);
        py.resize(numParticles);
        pm.resize(numParticles);
        nextInLeaf.resize(numParticles);
        nodes.reserve(std::max(8, numParticles * 4));
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = (int)particles.size();
        if ((int)newParticles.size() != n) newParticles.resize(n);

        if ((int)px.size() != n) {
            px.resize(n);
            py.resize(n);
            pm.resize(n);
            nextInLeaf.resize(n);
        }

        float minx = FLT_MAX, miny = FLT_MAX, maxx = -FLT_MAX, maxy = -FLT_MAX;

        #pragma omp parallel for schedule(static) reduction(min:minx,miny) reduction(max:maxx,maxy)
        for (int i = 0; i < n; i++) {
            const auto &p = particles[i];
            float x = p.position.x;
            float y = p.position.y;
            px[i] = x;
            py[i] = y;
            pm[i] = p.mass;
            nextInLeaf[i] = -1;
            minx = std::min(minx, x);
            miny = std::min(miny, y);
            maxx = std::max(maxx, x);
            maxy = std::max(maxy, y);
        }

        float cx = 0.5f * (minx + maxx);
        float cy = 0.5f * (miny + maxy);
        float rx = maxx - minx;
        float ry = maxy - miny;
        float range = std::max(rx, ry);
        if (!(range > 0.0f)) range = 1.0f;
        float half = 0.5f * range * 1.02f + 1e-2f;

        nodes.clear();
        Node root;
        root.cx = cx;
        root.cy = cy;
        root.half = half;
        root.mass = 0.0f;
        root.comx = cx;
        root.comy = cy;
        root.head = -1;
        root.child[0] = root.child[1] = root.child[2] = root.child[3] = -1;
        nodes.push_back(root);

        for (int i = 0; i < n; i++) insertParticle(0, i, 0);
        computeMassCOM();

        const float r = params.cullRadius;
        const float r2 = r * r;
        const float dt = params.deltaTime;
        const float theta2 = theta * theta;

        #pragma omp parallel
        {
            std::vector<int> stack;
            stack.reserve(256);

            Particle agg;
            agg.id = -1;
            agg.velocity = Vec2(0.0f, 0.0f);

            #pragma omp for schedule(guided, 32)
            for (int i = 0; i < n; i++) {
                const Particle &pi = particles[i];
                const float pix = px[i];
                const float piy = py[i];

                float fx = 0.0f, fy = 0.0f;

                stack.clear();
                stack.push_back(0);

                while (!stack.empty()) {
                    int idx = stack.back();
                    stack.pop_back();

                    const Node &nd = nodes[idx];
                    if (!(nd.mass > 0.0f)) continue;

                    float adx = std::fabs(pix - nd.cx);
                    float ady = std::fabs(piy - nd.cy);

                    float dx = adx - nd.half;
                    float dy = ady - nd.half;
                    if (dx < 0.0f) dx = 0.0f;
                    if (dy < 0.0f) dy = 0.0f;
                    float minDist2 = dx * dx + dy * dy;
                    if (minDist2 > r2) continue;

                    if (nd.head != -2) {
                        for (int p = nd.head; p != -1; p = nextInLeaf[p]) {
                            if (p == i) continue;
                            float ddx = px[p] - pix;
                            float ddy = py[p] - piy;
                            float dist2 = ddx * ddx + ddy * ddy;
                            if (dist2 > r2 || dist2 < 1e-6f) continue;
                            Vec2 f = computeForce(pi, particles[p], r);
                            fx += f.x;
                            fy += f.y;
                        }
                        continue;
                    }

                    float mdx = adx + nd.half;
                    float mdy = ady + nd.half;
                    bool fullyInside = (mdx * mdx + mdy * mdy <= r2);
                    bool containsSelf = (adx <= nd.half && ady <= nd.half);

                    if (fullyInside && !containsSelf) {
                        float cdx = nd.comx - pix;
                        float cdy = nd.comy - piy;
                        float dist2 = cdx * cdx + cdy * cdy;
                        float size = nd.half * 2.0f;
                        if (dist2 > 1e-6f && (size * size <= theta2 * dist2)) {
                            agg.mass = nd.mass;
                            agg.position = Vec2(nd.comx, nd.comy);
                            Vec2 f = computeForce(pi, agg, r);
                            fx += f.x;
                            fy += f.y;
                            continue;
                        }
                    }

                    for (int k = 0; k < 4; k++) {
                        int c = nd.child[k];
                        if (c != -1 && nodes[c].mass > 0.0f) stack.push_back(c);
                    }
                }

                newParticles[i] = updateParticle(pi, Vec2(fx, fy), dt);
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}