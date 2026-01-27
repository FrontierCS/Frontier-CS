#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horiz = true; // true: horizontal, false: vertical
    int fixed = 0;     // row if horiz, col if vert
    int len = 0;       // 2 or 3
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

class DistMap {
    static constexpr uint64_t EMPTY = UINT64_MAX;

    vector<uint64_t> keys;
    vector<uint16_t> vals;
    size_t mask = 0;
    size_t sz = 0;

    void rehash(size_t newCap) {
        size_t cap = 1;
        while (cap < newCap) cap <<= 1;
        vector<uint64_t> oldKeys = std::move(keys);
        vector<uint16_t> oldVals = std::move(vals);

        keys.assign(cap, EMPTY);
        vals.assign(cap, 0);
        mask = cap - 1;
        sz = 0;

        for (size_t i = 0; i < oldKeys.size(); i++) {
            uint64_t k = oldKeys[i];
            if (k == EMPTY) continue;
            uint16_t v = oldVals[i];
            size_t idx = splitmix64(k) & mask;
            while (keys[idx] != EMPTY) idx = (idx + 1) & mask;
            keys[idx] = k;
            vals[idx] = v;
            sz++;
        }
    }

public:
    explicit DistMap(size_t initialCap = (1u << 20)) {
        rehash(initialCap);
    }

    bool get(uint64_t k, uint16_t &out) const {
        size_t idx = splitmix64(k) & mask;
        while (true) {
            uint64_t kk = keys[idx];
            if (kk == EMPTY) return false;
            if (kk == k) {
                out = vals[idx];
                return true;
            }
            idx = (idx + 1) & mask;
        }
    }

    bool relax(uint64_t k, uint16_t newv) {
        if ((sz + 1) * 10 >= (mask + 1) * 7) rehash((mask + 1) * 2);

        size_t idx = splitmix64(k) & mask;
        while (true) {
            uint64_t kk = keys[idx];
            if (kk == EMPTY) {
                keys[idx] = k;
                vals[idx] = newv;
                sz++;
                return true;
            }
            if (kk == k) {
                if (newv < vals[idx]) {
                    vals[idx] = newv;
                    return true;
                }
                return false;
            }
            idx = (idx + 1) & mask;
        }
    }
};

struct Node {
    uint64_t s;
    uint16_t g;
    uint16_t f;
};
struct NodeCmp {
    bool operator()(const Node& a, const Node& b) const {
        if (a.f != b.f) return a.f > b.f;
        return a.g > b.g;
    }
};

static int nVehicles;
static vector<Vehicle> veh;

static inline void decodeState(uint64_t s, int *pos) {
    for (int i = 1; i <= nVehicles; i++) {
        pos[i] = int((s >> (4 * (i - 1))) & 0xFULL);
    }
}

static inline int heuristic(const int *pos) {
    int redPos = pos[1];
    if (redPos >= 6) return 0;

    int h = 6 - redPos;
    int redRight = redPos + veh[1].len - 1;
    if (redRight >= 5) return h;

    int startCol = redRight + 1;
    unsigned mask = 0;
    for (int j = 2; j <= nVehicles; j++) {
        const auto &vj = veh[j];
        if (vj.horiz) {
            if (vj.fixed != 2) continue;
            int left = pos[j];
            int right = left + vj.len - 1;
            if (right >= startCol && left <= 5) mask |= (1u << j);
        } else {
            int col = vj.fixed;
            if (col < startCol || col > 5) continue;
            int top = pos[j];
            int bot = top + vj.len - 1;
            if (top <= 2 && 2 <= bot) mask |= (1u << j);
        }
    }
    h += __builtin_popcount(mask);
    return h;
}

static inline void buildOcc(const int *pos, int *occ) {
    memset(occ, 0, 36 * sizeof(int));
    for (int i = 1; i <= nVehicles; i++) {
        const auto &v = veh[i];
        if (v.horiz) {
            int r = v.fixed;
            int c0 = pos[i];
            for (int k = 0; k < v.len; k++) {
                int c = c0 + k;
                if (c < 0 || c >= 6) continue;
                if (r < 0 || r >= 6) continue;
                occ[r * 6 + c] = i;
            }
        } else {
            int c = v.fixed;
            int r0 = pos[i];
            for (int k = 0; k < v.len; k++) {
                int r = r0 + k;
                if (r < 0 || r >= 6) continue;
                if (c < 0 || c >= 6) continue;
                occ[r * 6 + c] = i;
            }
        }
    }
}

static int solveAStar(uint64_t start) {
    int pos[16];
    decodeState(start, pos);
    if (pos[1] == 6) return 0;

    DistMap dist(1u << 20);
    priority_queue<Node, vector<Node>, NodeCmp> pq;

    uint16_t g0 = 0;
    uint16_t f0 = uint16_t(g0 + heuristic(pos));
    dist.relax(start, g0);
    pq.push(Node{start, g0, f0});

    int occ[36];

    while (!pq.empty()) {
        Node cur = pq.top();
        pq.pop();

        uint16_t bestg;
        if (!dist.get(cur.s, bestg) || bestg != cur.g) continue;

        decodeState(cur.s, pos);
        if (pos[1] == 6) return cur.g;

        buildOcc(pos, occ);

        for (int i = 1; i <= nVehicles; i++) {
            const auto &v = veh[i];
            const int shift = 4 * (i - 1);
            const uint64_t maskBits = 0xFULL << shift;
            int pi = pos[i];

            if (v.horiz) {
                int r = v.fixed;
                // Left
                if (pi > 0) {
                    int enterC = pi - 1;
                    if (occ[r * 6 + enterC] == 0) {
                        int newp = pi - 1;
                        uint64_t s2 = (cur.s & ~maskBits) | (uint64_t(newp) << shift);
                        uint16_t ng = uint16_t(cur.g + 1);
                        int old = pos[i];
                        pos[i] = newp;
                        uint16_t nf = uint16_t(ng + heuristic(pos));
                        pos[i] = old;
                        if (dist.relax(s2, ng)) pq.push(Node{s2, ng, nf});
                    }
                }
                // Right
                if (i == 1) {
                    if (pi < 6) {
                        int enterC = pi + v.len;
                        bool ok = true;
                        if (enterC < 6) {
                            if (occ[r * 6 + enterC] != 0) ok = false;
                        }
                        if (ok) {
                            int newp = pi + 1;
                            uint64_t s2 = (cur.s & ~maskBits) | (uint64_t(newp) << shift);
                            uint16_t ng = uint16_t(cur.g + 1);
                            int old = pos[i];
                            pos[i] = newp;
                            uint16_t nf = uint16_t(ng + heuristic(pos));
                            pos[i] = old;
                            if (dist.relax(s2, ng)) pq.push(Node{s2, ng, nf});
                        }
                    }
                } else {
                    int enterC = pi + v.len;
                    if (enterC < 6) {
                        if (occ[r * 6 + enterC] == 0) {
                            int newp = pi + 1;
                            uint64_t s2 = (cur.s & ~maskBits) | (uint64_t(newp) << shift);
                            uint16_t ng = uint16_t(cur.g + 1);
                            int old = pos[i];
                            pos[i] = newp;
                            uint16_t nf = uint16_t(ng + heuristic(pos));
                            pos[i] = old;
                            if (dist.relax(s2, ng)) pq.push(Node{s2, ng, nf});
                        }
                    }
                }
            } else {
                int c = v.fixed;
                // Up
                if (pi > 0) {
                    int enterR = pi - 1;
                    if (occ[enterR * 6 + c] == 0) {
                        int newp = pi - 1;
                        uint64_t s2 = (cur.s & ~maskBits) | (uint64_t(newp) << shift);
                        uint16_t ng = uint16_t(cur.g + 1);
                        int old = pos[i];
                        pos[i] = newp;
                        uint16_t nf = uint16_t(ng + heuristic(pos));
                        pos[i] = old;
                        if (dist.relax(s2, ng)) pq.push(Node{s2, ng, nf});
                    }
                }
                // Down
                int enterR = pi + v.len;
                if (enterR < 6) {
                    if (occ[enterR * 6 + c] == 0) {
                        int newp = pi + 1;
                        uint64_t s2 = (cur.s & ~maskBits) | (uint64_t(newp) << shift);
                        uint16_t ng = uint16_t(cur.g + 1);
                        int old = pos[i];
                        pos[i] = newp;
                        uint16_t nf = uint16_t(ng + heuristic(pos));
                        pos[i] = old;
                        if (dist.relax(s2, ng)) pq.push(Node{s2, ng, nf});
                    }
                }
            }
        }
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int a[6][6];
    int mx = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (!(cin >> a[r][c])) return 0;
            mx = max(mx, a[r][c]);
        }
    }

    nVehicles = mx;
    vector<vector<pair<int,int>>> cells(nVehicles + 1);
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            int id = a[r][c];
            if (id > 0) cells[id].push_back({r, c});
        }
    }

    veh.assign(nVehicles + 1, Vehicle{});
    vector<int> initPos(nVehicles + 1, 0);

    for (int i = 1; i <= nVehicles; i++) {
        auto &cc = cells[i];
        int len = (int)cc.size();
        int minR = 10, maxR = -1, minC = 10, maxC = -1;
        for (auto [r, c] : cc) {
            minR = min(minR, r);
            maxR = max(maxR, r);
            minC = min(minC, c);
            maxC = max(maxC, c);
        }
        Vehicle v;
        v.len = len;
        if (minR == maxR) {
            v.horiz = true;
            v.fixed = minR;
            initPos[i] = minC;
        } else {
            v.horiz = false;
            v.fixed = minC;
            initPos[i] = minR;
        }
        veh[i] = v;
    }

    uint64_t start = 0;
    for (int i = 1; i <= nVehicles; i++) {
        start |= (uint64_t(initPos[i]) << (4 * (i - 1)));
    }

    int minSteps = solveAStar(start);
    if (minSteps < 0) minSteps = 0;

    cout << minSteps << " " << 0 << "\n";
    return 0;
}