#include "world.h"
#include <omp.h>
#include <vector>
#include <cmath>
#include <algorithm>
#include <limits>
#include <cstdint>

class MySimulator : public Simulator {
private:
    static constexpr float G = 0.01f;

    struct Node {
        float cx = 0.0f, cy = 0.0f;
        float half = 0.0f;

        float mass = 0.0f;
        float sumx = 0.0f, sumy = 0.0f; // weighted sums
        float comx = 0.0f, comy = 0.0f;

        int child[4] = {-1, -1, -1, -1}; // 0: (x<cx,y<cy), 1: (x>=cx,y<cy), 2: (x<cx,y>=cy), 3: (x>=cx,y>=cy)
        int count = 0;                  // >=0 leaf; -1 internal

        static constexpr int CAP = 12;
        int idx[CAP];
    };

    int numThreads = 16;
    int nCached = 0;

    std::vector<float> px, py, pm;

    std::vector<Node> nodes;
    std::vector<int> order; // for postorder aggregate computation

    static inline void boxMinMaxDist2(float px, float py, const Node &nd, float &minD2, float &maxD2) {
        float dx = std::fabs(px - nd.cx);
        float dy = std::fabs(py - nd.cy);

        float ox = dx - nd.half;
        float oy = dy - nd.half;
        if (ox < 0.0f) ox = 0.0f;
        if (oy < 0.0f) oy = 0.0f;
        minD2 = ox * ox + oy * oy;

        float fx = dx + nd.half;
        float fy = dy + nd.half;
        maxD2 = fx * fx + fy * fy;
    }

    static inline bool containsPoint(float x, float y, const Node &nd) {
        return (std::fabs(x - nd.cx) <= nd.half) && (std::fabs(y - nd.cy) <= nd.half);
    }

    inline int newNode(float cx, float cy, float half) {
        Node nd;
        nd.cx = cx; nd.cy = cy; nd.half = half;
        nd.count = 0;
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }

    inline int quadrant(float x, float y, const Node &nd) const {
        int qx = (x >= nd.cx) ? 1 : 0;
        int qy = (y >= nd.cy) ? 1 : 0;
        return (qy << 1) | qx;
    }

    void splitNode(int ni, int depth) {
        Node &nd = nodes[ni];
        float h2 = nd.half * 0.5f;
        float off = h2;

        int c0 = newNode(nd.cx - off, nd.cy - off, h2);
        int c1 = newNode(nd.cx + off, nd.cy - off, h2);
        int c2 = newNode(nd.cx - off, nd.cy + off, h2);
        int c3 = newNode(nd.cx + off, nd.cy + off, h2);
        nd.child[0] = c0; nd.child[1] = c1; nd.child[2] = c2; nd.child[3] = c3;

        int oldCount = nd.count;
        int oldIdx[Node::CAP];
        for (int k = 0; k < oldCount; k++) oldIdx[k] = nd.idx[k];

        nd.count = -1; // internal

        for (int k = 0; k < oldCount; k++) {
            int pi = oldIdx[k];
            insertParticle(ni, pi, depth); // re-insert from this node; will go into children
        }
    }

    void insertParticle(int ni, int piIndex, int depth) {
        Node &nd = nodes[ni];

        if (nd.count >= 0) { // leaf
            if (nd.count < Node::CAP || depth >= 24 || nd.half <= 1e-4f) {
                nd.idx[nd.count++] = piIndex;
                return;
            }
            // split and retry insertion
            splitNode(ni, depth);
            insertParticle(ni, piIndex, depth);
            return;
        }

        // internal
        int q = quadrant(px[piIndex], py[piIndex], nd);
        int ci = nd.child[q];
        insertParticle(ci, piIndex, depth + 1);
    }

    void buildTree(int n) {
        // bounding box
        float minx = std::numeric_limits<float>::infinity();
        float maxx = -std::numeric_limits<float>::infinity();
        float miny = std::numeric_limits<float>::infinity();
        float maxy = -std::numeric_limits<float>::infinity();

        #pragma omp parallel for reduction(min:minx,miny) reduction(max:maxx,maxy) schedule(static)
        for (int i = 0; i < n; i++) {
            float x = px[i], y = py[i];
            if (x < minx) minx = x;
            if (x > maxx) maxx = x;
            if (y < miny) miny = y;
            if (y > maxy) maxy = y;
        }

        float cx = 0.5f * (minx + maxx);
        float cy = 0.5f * (miny + maxy);
        float rx = maxx - minx;
        float ry = maxy - miny;
        float range = std::max(rx, ry);
        float half = 0.5f * range + 1e-3f;
        if (half < 1e-3f) half = 1e-3f;

        nodes.clear();
        order.clear();
        nodes.reserve((size_t)std::max(2048, n * 2));
        order.reserve((size_t)std::max(2048, n * 2));

        int root = newNode(cx, cy, half);

        for (int i = 0; i < n; i++) {
            insertParticle(root, i, 0);
        }

        // create traversal order (preorder), then aggregate in reverse for postorder
        std::vector<int> st;
        st.reserve(1024);
        st.push_back(root);
        while (!st.empty()) {
            int ni = st.back();
            st.pop_back();
            order.push_back(ni);
            Node &nd = nodes[ni];
            if (nd.count < 0) {
                // push children
                for (int k = 0; k < 4; k++) {
                    int ci = nd.child[k];
                    if (ci != -1) st.push_back(ci);
                }
            }
        }

        // reset aggregates
        for (auto &nd : nodes) {
            nd.mass = 0.0f;
            nd.sumx = 0.0f;
            nd.sumy = 0.0f;
            nd.comx = nd.cx;
            nd.comy = nd.cy;
        }

        for (int oi = (int)order.size() - 1; oi >= 0; oi--) {
            int ni = order[oi];
            Node &nd = nodes[ni];

            if (nd.count >= 0) {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int k = 0; k < nd.count; k++) {
                    int pi = nd.idx[k];
                    float pmass = pm[pi];
                    m += pmass;
                    sx += pmass * px[pi];
                    sy += pmass * py[pi];
                }
                nd.mass = m;
                nd.sumx = sx;
                nd.sumy = sy;
                if (m > 0.0f) {
                    nd.comx = sx / m;
                    nd.comy = sy / m;
                } else {
                    nd.comx = nd.cx;
                    nd.comy = nd.cy;
                }
            } else {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int k = 0; k < 4; k++) {
                    int ci = nd.child[k];
                    if (ci == -1) continue;
                    const Node &ch = nodes[ci];
                    m += ch.mass;
                    sx += ch.sumx;
                    sy += ch.sumy;
                }
                nd.mass = m;
                nd.sumx = sx;
                nd.sumy = sy;
                if (m > 0.0f) {
                    nd.comx = sx / m;
                    nd.comy = sy / m;
                } else {
                    nd.comx = nd.cx;
                    nd.comy = nd.cy;
                }
            }
        }
    }

    static inline void addAccelFromMassPoint(float tx, float ty, float axp, float ayp, float amass,
                                            float cullRadius, float rInner, float rQuarter,
                                            float &outAx, float &outAy) {
        float dx = axp - tx;
        float dy = ayp - ty;
        float dist2 = dx * dx + dy * dy;
        if (dist2 < 1e-12f) return;

        float dist = std::sqrt(dist2);
        if (dist < 1e-3f) return;
        if (dist > cullRadius) return;

        float invDist = 1.0f / dist;
        float ux = dx * invDist;
        float uy = dy * invDist;

        float distEff = (dist < 1e-1f) ? 1e-1f : dist;
        float inv = G / (distEff * distEff);
        float s = amass * inv;

        if (dist > rInner) {
            float decay = 1.0f - (dist - rInner) / rQuarter;
            s *= decay;
        }

        outAx += ux * s;
        outAy += uy * s;
    }

public:
    void init(int numParticles, StepParameters /*params*/) override {
        nCached = numParticles;
        numThreads = std::min(16, omp_get_max_threads());
        omp_set_dynamic(0);
        omp_set_num_threads(numThreads);

        px.resize(numParticles);
        py.resize(numParticles);
        pm.resize(numParticles);

        nodes.reserve((size_t)std::max(2048, numParticles * 2));
        order.reserve((size_t)std::max(2048, numParticles * 2));
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        const int n = (int)particles.size();
        if (n == 0) return;

        if ((int)px.size() != n) {
            init(n, params);
        }

        #pragma omp parallel for schedule(static)
        for (int i = 0; i < n; i++) {
            px[i] = particles[i].position.x;
            py[i] = particles[i].position.y;
            pm[i] = particles[i].mass;
        }

        buildTree(n);

        const float r = params.cullRadius;
        const float r2 = r * r;
        const float rInner = r * 0.75f;
        const float rInner2 = rInner * rInner;
        const float rQuarter = r * 0.25f;
        const float dt = params.deltaTime;

        const float thetaInner = 0.30f;
        const float thetaDecay = 0.20f;
        const float thetaInner2 = thetaInner * thetaInner;
        const float thetaDecay2 = thetaDecay * thetaDecay;

        #pragma omp parallel
        {
            std::vector<int> st;
            st.reserve(512);

            #pragma omp for schedule(guided, 64)
            for (int i = 0; i < n; i++) {
                float tx = px[i], ty = py[i];
                float ax = 0.0f, ay = 0.0f;

                st.clear();
                st.push_back(0); // root

                while (!st.empty()) {
                    int ni = st.back();
                    st.pop_back();
                    const Node &nd = nodes[ni];
                    if (nd.mass <= 0.0f) continue;

                    float minD2, maxD2;
                    boxMinMaxDist2(tx, ty, nd, minD2, maxD2);
                    if (minD2 > r2) continue;

                    if (nd.count >= 0) {
                        // leaf: exact per particle
                        for (int k = 0; k < nd.count; k++) {
                            int j = nd.idx[k];
                            if (j == i) continue;

                            float dx = px[j] - tx;
                            float dy = py[j] - ty;
                            float d2 = dx * dx + dy * dy;
                            if (d2 > r2 || d2 < 1e-12f) continue;

                            float dist = std::sqrt(d2);
                            if (dist < 1e-3f || dist > r) continue;

                            float invDist = 1.0f / dist;
                            float ux = dx * invDist;
                            float uy = dy * invDist;

                            float distEff = (dist < 1e-1f) ? 1e-1f : dist;
                            float inv = G / (distEff * distEff);
                            float s = pm[j] * inv;

                            if (dist > rInner) {
                                float decay = 1.0f - (dist - rInner) / rQuarter;
                                s *= decay;
                            }

                            ax += ux * s;
                            ay += uy * s;
                        }
                        continue;
                    }

                    // internal node
                    bool contains = containsPoint(tx, ty, nd);
                    if (contains) {
                        for (int c = 0; c < 4; c++) {
                            int ci = nd.child[c];
                            if (ci != -1 && nodes[ci].mass > 0.0f) st.push_back(ci);
                        }
                        continue;
                    }

                    if (maxD2 <= r2) {
                        bool allInner = (maxD2 <= rInner2);
                        bool allDecay = (minD2 >= rInner2);
                        float useTheta2 = -1.0f;
                        if (allInner) useTheta2 = thetaInner2;
                        else if (allDecay) useTheta2 = thetaDecay2;

                        if (useTheta2 > 0.0f) {
                            float dcx = tx - nd.cx;
                            float dcy = ty - nd.cy;
                            float dist2Center = dcx * dcx + dcy * dcy + 1e-12f;
                            float w = nd.half * 2.0f;
                            float w2 = w * w;
                            if (w2 < useTheta2 * dist2Center) {
                                addAccelFromMassPoint(tx, ty, nd.comx, nd.comy, nd.mass, r, rInner, rQuarter, ax, ay);
                                continue;
                            }
                        }
                    }

                    // traverse children
                    for (int c = 0; c < 4; c++) {
                        int ci = nd.child[c];
                        if (ci != -1 && nodes[ci].mass > 0.0f) st.push_back(ci);
                    }
                }

                Particle out = particles[i];
                out.velocity.x = out.velocity.x + ax * dt;
                out.velocity.y = out.velocity.y + ay * dt;
                out.position.x = out.position.x + out.velocity.x * dt;
                out.position.y = out.position.y + out.velocity.y * dt;
                newParticles[i] = out;
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}