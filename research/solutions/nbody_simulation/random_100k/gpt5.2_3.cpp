#include "world.h"
#include <omp.h>

#include <vector>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <cstdint>

class MySimulator : public Simulator {
private:
    static constexpr int LEAF_CAP = 8;
    static constexpr int MAX_DEPTH = 18;
    static constexpr float MIN_SIZE = 1e-4f;

    struct Node {
        float minx = 0.0f, miny = 0.0f, size = 0.0f;
        int child[4] = {-1, -1, -1, -1}; // 0: (0,0), 1: (1,0), 2: (0,1), 3: (1,1)
        int count = 0;
        int p[LEAF_CAP];
        std::vector<int> extra; // only used if max-depth reached with too many particles
        float mass = 0.0f;
        float comx = 0.0f, comy = 0.0f;
    };

    int numThreads = 16;

    std::vector<Node> nodes;
    std::vector<int> order;

    std::vector<float> px, py, vx, vy, pm;

    inline int newNode(float minx, float miny, float size) {
        Node n;
        n.minx = minx;
        n.miny = miny;
        n.size = size;
        nodes.push_back(std::move(n));
        return (int)nodes.size() - 1;
    }

    inline int quadrant(const Node &n, float x, float y) const {
        float midx = n.minx + n.size * 0.5f;
        float midy = n.miny + n.size * 0.5f;
        int q = (x >= midx) ? 1 : 0;
        q |= (y >= midy) ? 2 : 0;
        return q;
    }

    inline void subdivide(int idx) {
        Node &n = nodes[idx];
        float h = n.size * 0.5f;
        for (int q = 0; q < 4; q++) {
            float cx = n.minx + ((q & 1) ? h : 0.0f);
            float cy = n.miny + ((q & 2) ? h : 0.0f);
            n.child[q] = newNode(cx, cy, h);
        }
    }

    void insertParticle(int idx, int pid, int depth) {
        Node &n = nodes[idx];
        if (n.child[0] == -1) {
            if (n.count < LEAF_CAP) {
                n.p[n.count++] = pid;
                return;
            }
            if (depth >= MAX_DEPTH || n.size <= MIN_SIZE) {
                n.extra.push_back(pid);
                return;
            }

            int tmp[LEAF_CAP + 1];
            for (int k = 0; k < LEAF_CAP; k++) tmp[k] = n.p[k];
            tmp[LEAF_CAP] = pid;

            n.count = 0;
            subdivide(idx);

            for (int k = 0; k < LEAF_CAP + 1; k++) {
                int id = tmp[k];
                const Node &nn = nodes[idx];
                int q = quadrant(nn, px[id], py[id]);
                insertParticle(nn.child[q], id, depth + 1);
            }
            return;
        } else {
            int q = quadrant(n, px[pid], py[pid]);
            insertParticle(n.child[q], pid, depth + 1);
        }
    }

    inline float minDist2ToAABB(const Node &n, float x, float y) const {
        float maxx = n.minx + n.size;
        float maxy = n.miny + n.size;
        float dx = 0.0f;
        if (x < n.minx) dx = n.minx - x;
        else if (x > maxx) dx = x - maxx;
        float dy = 0.0f;
        if (y < n.miny) dy = n.miny - y;
        else if (y > maxy) dy = y - maxy;
        return dx * dx + dy * dy;
    }

    inline float maxDist2ToAABB(const Node &n, float x, float y) const {
        float maxx = n.minx + n.size;
        float maxy = n.miny + n.size;
        float dx0 = std::fabs(x - n.minx);
        float dx1 = std::fabs(x - maxx);
        float dy0 = std::fabs(y - n.miny);
        float dy1 = std::fabs(y - maxy);
        float dx = (dx0 > dx1) ? dx0 : dx1;
        float dy = (dy0 > dy1) ? dy0 : dy1;
        return dx * dx + dy * dy;
    }

    inline bool containsPointHalfOpen(const Node &n, float x, float y) const {
        float maxx = n.minx + n.size;
        float maxy = n.miny + n.size;
        return (x >= n.minx && x < maxx && y >= n.miny && y < maxy);
    }

    inline void addForcePair(float tx, float ty, float tmass,
                             float ax, float ay, float amass,
                             float r, float r2, float decayStart, float invDecayRange,
                             float &fx, float &fy) const {
        float dx = ax - tx;
        float dy = ay - ty;
        float dist2 = dx * dx + dy * dy;
        if (dist2 < 1e-6f || dist2 >= r2) return;

        float dist = std::sqrt(dist2);
        if (dist < 1e-3f) return;

        float invDist = 1.0f / dist;
        float dirx = dx * invDist;
        float diry = dy * invDist;

        float d = (dist < 1e-1f) ? 1e-1f : dist;

        const float G = 0.01f;
        float invd2 = 1.0f / (d * d);
        float fmag = (G * tmass * amass) * invd2;

        if (d > decayStart) {
            float decay = 1.0f - (d - decayStart) * invDecayRange;
            if (decay <= 0.0f) return;
            fmag *= decay;
        }

        fx += dirx * fmag;
        fy += diry * fmag;
    }

    void buildTree() {
        int n = (int)px.size();
        nodes.clear();
        order.clear();
        if (n == 0) return;

        float minx = px[0], maxx = px[0];
        float miny = py[0], maxy = py[0];
        for (int i = 1; i < n; i++) {
            float x = px[i], y = py[i];
            if (x < minx) minx = x;
            if (x > maxx) maxx = x;
            if (y < miny) miny = y;
            if (y > maxy) maxy = y;
        }

        float spanx = maxx - minx;
        float spany = maxy - miny;
        float size = (spanx > spany) ? spanx : spany;
        float pad = 1e-3f + 0.01f * size;
        size = size + 2.0f * pad;
        minx -= pad;
        miny -= pad;

        nodes.reserve((size_t)std::max(4 * n, 1024));
        newNode(minx, miny, size);

        for (int i = 0; i < n; i++) {
            insertParticle(0, i, 0);
        }

        // Build traversal order (preorder), then compute mass/COM bottom-up.
        order.reserve(nodes.size());
        std::vector<int> st;
        st.reserve(256);
        st.push_back(0);
        while (!st.empty()) {
            int idx = st.back();
            st.pop_back();
            order.push_back(idx);
            Node &nd = nodes[idx];
            if (nd.child[0] != -1) {
                // push in reverse so 0 is processed first in the implicit traversal
                st.push_back(nd.child[3]);
                st.push_back(nd.child[2]);
                st.push_back(nd.child[1]);
                st.push_back(nd.child[0]);
            }
        }

        for (int oi = (int)order.size() - 1; oi >= 0; oi--) {
            int idx = order[oi];
            Node &nd = nodes[idx];
            if (nd.child[0] == -1) {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int k = 0; k < nd.count; k++) {
                    int pid = nd.p[k];
                    float mm = pm[pid];
                    m += mm;
                    sx += mm * px[pid];
                    sy += mm * py[pid];
                }
                for (int pid : nd.extra) {
                    float mm = pm[pid];
                    m += mm;
                    sx += mm * px[pid];
                    sy += mm * py[pid];
                }
                nd.mass = m;
                if (m > 0.0f) {
                    nd.comx = sx / m;
                    nd.comy = sy / m;
                } else {
                    nd.comx = nd.minx + nd.size * 0.5f;
                    nd.comy = nd.miny + nd.size * 0.5f;
                }
            } else {
                float m = 0.0f, sx = 0.0f, sy = 0.0f;
                for (int c = 0; c < 4; c++) {
                    int ci = nd.child[c];
                    const Node &ch = nodes[ci];
                    float cm = ch.mass;
                    m += cm;
                    sx += cm * ch.comx;
                    sy += cm * ch.comy;
                }
                nd.mass = m;
                if (m > 0.0f) {
                    nd.comx = sx / m;
                    nd.comy = sy / m;
                } else {
                    nd.comx = nd.minx + nd.size * 0.5f;
                    nd.comy = nd.miny + nd.size * 0.5f;
                }
            }
        }
    }

public:
    void init(int numParticles, StepParameters) override {
        int hw = omp_get_max_threads();
        numThreads = std::min(16, hw > 0 ? hw : 16);
        omp_set_num_threads(numThreads);

        px.resize(numParticles);
        py.resize(numParticles);
        vx.resize(numParticles);
        vy.resize(numParticles);
        pm.resize(numParticles);

        nodes.clear();
        order.clear();
    }

    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        int n = (int)particles.size();
        if ((int)newParticles.size() != n) newParticles.resize(n);
        if ((int)px.size() != n) {
            px.resize(n); py.resize(n); vx.resize(n); vy.resize(n); pm.resize(n);
        }

        for (int i = 0; i < n; i++) {
            px[i] = particles[i].position.x;
            py[i] = particles[i].position.y;
            vx[i] = particles[i].velocity.x;
            vy[i] = particles[i].velocity.y;
            pm[i] = particles[i].mass;
        }

        buildTree();
        if (nodes.empty()) {
            for (int i = 0; i < n; i++) newParticles[i] = particles[i];
            return;
        }

        const float r = params.cullRadius;
        const float r2 = r * r;
        const float decayStart = r * 0.75f;
        const float invDecayRange = (r > 0.0f) ? (1.0f / (r * 0.25f)) : 0.0f;
        const float dt = params.deltaTime;

        const float theta = 0.35f;
        const float theta2 = theta * theta;

        #pragma omp parallel
        {
            std::vector<int> st;
            st.reserve(256);

            #pragma omp for schedule(guided, 32)
            for (int i = 0; i < n; i++) {
                float tx = px[i], ty = py[i], tm = pm[i];
                float fx = 0.0f, fy = 0.0f;

                st.clear();
                st.push_back(0);

                while (!st.empty()) {
                    int idx = st.back();
                    st.pop_back();
                    const Node &nd = nodes[idx];

                    if (nd.mass <= 0.0f) continue;

                    float mind2 = minDist2ToAABB(nd, tx, ty);
                    if (mind2 >= r2) continue;

                    bool leaf = (nd.child[0] == -1);
                    float maxd2 = maxDist2ToAABB(nd, tx, ty);
                    bool fullyInside = (maxd2 < r2);
                    bool contains = containsPointHalfOpen(nd, tx, ty);

                    if (fullyInside && !contains) {
                        float dx = nd.comx - tx;
                        float dy = nd.comy - ty;
                        float dist2 = dx * dx + dy * dy;
                        if (dist2 > 1e-6f) {
                            // opening criterion without sqrt: (size / dist) < theta
                            if ((nd.size * nd.size) < (theta2 * dist2)) {
                                addForcePair(tx, ty, tm, nd.comx, nd.comy, nd.mass, r, r2, decayStart, invDecayRange, fx, fy);
                                continue;
                            }
                        }
                    }

                    if (leaf) {
                        for (int k = 0; k < nd.count; k++) {
                            int j = nd.p[k];
                            if (j == i) continue;
                            addForcePair(tx, ty, tm, px[j], py[j], pm[j], r, r2, decayStart, invDecayRange, fx, fy);
                        }
                        for (int j : nd.extra) {
                            if (j == i) continue;
                            addForcePair(tx, ty, tm, px[j], py[j], pm[j], r, r2, decayStart, invDecayRange, fx, fy);
                        }
                    } else {
                        // push children in reverse so 0 is processed first
                        st.push_back(nd.child[3]);
                        st.push_back(nd.child[2]);
                        st.push_back(nd.child[1]);
                        st.push_back(nd.child[0]);
                    }
                }

                float invm = 1.0f / tm;
                float nvx = vx[i] + fx * (dt * invm);
                float nvy = vy[i] + fy * (dt * invm);
                float npx = tx + nvx * dt;
                float npy = ty + nvy * dt;

                Particle out = particles[i];
                out.velocity.x = nvx;
                out.velocity.y = nvy;
                out.position.x = npx;
                out.position.y = npy;
                newParticles[i] = out;
            }
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}