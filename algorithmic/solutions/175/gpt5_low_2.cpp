#include <bits/stdc++.h>
using namespace std;

static inline int fast_read_int() {
    int x = 0, s = 1, c = getchar_unlocked();
    while (c != '-' && (c < '0' || c > '9')) c = getchar_unlocked();
    if (c == '-') { s = -1; c = getchar_unlocked(); }
    while (c >= '0' && c <= '9') { x = x * 10 + (c - '0'); c = getchar_unlocked(); }
    return x * s;
}

struct RNG {
    uint64_t s;
    RNG(uint64_t seed = 88172645463393265ull) : s(seed) {}
    inline uint64_t next() {
        s ^= s << 7;
        s ^= s >> 9;
        return s;
    }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline int rand_int(int n) { return (int)(next() % n); }
    inline bool coin(double p) { return (next() >> 11) < (uint64_t)(p * (1ull << 53)); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = fast_read_int();
    int m = fast_read_int();

    vector<int> a, b, c;
    a.reserve(m); b.reserve(m); c.reserve(m);
    vector<int> posCnt(n+1,0), negCnt(n+1,0);

    for (int i = 0; i < m; ++i) {
        int x = fast_read_int();
        int y = fast_read_int();
        int z = fast_read_int();
        a.push_back(x);
        b.push_back(y);
        c.push_back(z);
        int vx = abs(x), vy = abs(y), vz = abs(z);
        if (x > 0) posCnt[vx]++; else negCnt[vx]++;
        if (y > 0) posCnt[vy]++; else negCnt[vy]++;
        if (z > 0) posCnt[vz]++; else negCnt[vz]++;
    }

    vector<uint8_t> val(n+1,0);
    for (int i = 1; i <= n; ++i) {
        val[i] = (posCnt[i] >= negCnt[i]) ? 1 : 0;
    }

    auto litId = [&](int lit)->int {
        if (lit > 0) return 2*(lit-1);
        else return 2*((-lit)-1)+1;
    };

    int L = 2*n;
    vector<int> head(L, -1);
    vector<int> nextOcc;
    vector<int> occClause;
    nextOcc.reserve(3LL*m);
    occClause.reserve(3LL*m);

    auto add_occ = [&](int lid, int cid){
        occClause.push_back(cid);
        nextOcc.push_back(head[lid]);
        head[lid] = (int)nextOcc.size()-1;
    };

    for (int i = 0; i < m; ++i) {
        add_occ(litId(a[i]), i);
        add_occ(litId(b[i]), i);
        add_occ(litId(c[i]), i);
    }

    vector<uint8_t> cnt(m,0);
    auto litTrue = [&](int lit)->bool {
        int v = abs(lit);
        bool x = val[v];
        return lit > 0 ? x : !x;
    };
    for (int i = 0; i < m; ++i) {
        uint8_t s = 0;
        s += litTrue(a[i]);
        s += litTrue(b[i]);
        s += litTrue(c[i]);
        cnt[i] = s;
    }

    vector<int> unsat;
    unsat.reserve(m);
    vector<int> idxInUnsat(m, -1);
    for (int i = 0; i < m; ++i) {
        if (cnt[i] == 0) {
            idxInUnsat[i] = (int)unsat.size();
            unsat.push_back(i);
        }
    }

    RNG rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto remove_unsat = [&](int cid){
        int idx = idxInUnsat[cid];
        if (idx == -1) return;
        int last = unsat.back();
        unsat[idx] = last;
        idxInUnsat[last] = idx;
        unsat.pop_back();
        idxInUnsat[cid] = -1;
    };
    auto add_unsat = [&](int cid){
        if (idxInUnsat[cid] != -1) return;
        idxInUnsat[cid] = (int)unsat.size();
        unsat.push_back(cid);
    };

    auto flipVar = [&](int v){
        uint8_t old = val[v];
        uint8_t nw = old ^ 1;
        val[v] = nw;

        int posId = 2*(v-1);
        int negId = posId + 1;

        if (old == 0 && nw == 1) {
            // pos: false->true => ++
            for (int e = head[posId]; e != -1; e = nextOcc[e]) {
                int cl = occClause[e];
                uint8_t nc = cnt[cl] + 1;
                if (nc == 1) remove_unsat(cl);
                cnt[cl] = nc;
            }
            // neg: true->false => --
            for (int e = head[negId]; e != -1; e = nextOcc[e]) {
                int cl = occClause[e];
                uint8_t nc = cnt[cl] - 1;
                cnt[cl] = nc;
                if (nc == 0) add_unsat(cl);
            }
        } else {
            // old 1 -> 0
            // pos: true->false => --
            for (int e = head[posId]; e != -1; e = nextOcc[e]) {
                int cl = occClause[e];
                uint8_t nc = cnt[cl] - 1;
                cnt[cl] = nc;
                if (nc == 0) add_unsat(cl);
            }
            // neg: false->true => ++
            for (int e = head[negId]; e != -1; e = nextOcc[e]) {
                int cl = occClause[e];
                uint8_t nc = cnt[cl] + 1;
                if (nc == 1) remove_unsat(cl);
                cnt[cl] = nc;
            }
        }
    };

    auto approx_delta = [&](int v)->int {
        uint8_t cur = val[v];
        int posId = 2*(v-1);
        int negId = posId + 1;
        int gain = 0, loss = 0;
        if (cur == 0) {
            // flip to 1: pos ++ when cnt==0; neg -- when cnt==1
            for (int e = head[posId]; e != -1; e = nextOcc[e]) if (cnt[occClause[e]] == 0) gain++;
            for (int e = head[negId]; e != -1; e = nextOcc[e]) if (cnt[occClause[e]] == 1) loss++;
        } else {
            // flip to 0: neg ++ when cnt==0; pos -- when cnt==1
            for (int e = head[negId]; e != -1; e = nextOcc[e]) if (cnt[occClause[e]] == 0) gain++;
            for (int e = head[posId]; e != -1; e = nextOcc[e]) if (cnt[occClause[e]] == 1) loss++;
        }
        return gain - loss;
    };

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.8; // seconds
    const double NOISE = 0.5;

    while (!unsat.empty()) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        int cidx = unsat[rng.rand_int((int)unsat.size())];
        int lits[3] = {a[cidx], b[cidx], c[cidx]};
        int vars[3] = {abs(lits[0]), abs(lits[1]), abs(lits[2])};

        int pick = -1;
        if (rng.coin(NOISE)) {
            pick = vars[rng.rand_int(3)];
        } else {
            int best = INT_MIN;
            int cand[3]; int cc = 0;
            for (int i = 0; i < 3; ++i) {
                int v = vars[i];
                int d = approx_delta(v);
                if (d > best) {
                    best = d; cand[0] = v; cc = 1;
                } else if (d == best) {
                    cand[cc++] = v;
                }
            }
            pick = cand[rng.rand_int(cc)];
        }
        flipVar(pick);
    }

    // Output assignment
    // 1 means TRUE, 0 means FALSE
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)val[i];
    }
    cout << '\n';
    return 0;
}