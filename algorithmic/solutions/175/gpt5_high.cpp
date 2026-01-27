#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
};

struct RNG {
    uint64_t state;
    RNG(uint64_t s = 0) {
        if (s == 0) {
            uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
            state = splitmix64(t ^ (uintptr_t)this);
        } else state = s;
    }
    static inline uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ull;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
        return x ^ (x >> 31);
    }
    inline uint64_t next() {
        state += 0x9e3779b97f4a7c15ull;
        return splitmix64(state);
    }
    inline uint32_t nextU32() { return (uint32_t)next(); }
    inline bool nextBool() { return (bool)(next() & 1ull); }
    inline int nextIntRange(int l, int r) { // inclusive
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    inline double nextDouble() {
        return (next() >> 11) * (1.0 / (1ull << 53));
    }
};

struct Clause { int l[3]; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n; long long mll;
    if (!fs.nextInt(n)) return 0;
    if (!fs.nextInt(mll)) return 0;
    int m = (int)mll;

    vector<Clause> clauses;
    clauses.resize(m);

    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0), occCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.nextInt(a); fs.nextInt(b); fs.nextInt(c);
        clauses[i].l[0] = a;
        clauses[i].l[1] = b;
        clauses[i].l[2] = c;
        int v0 = a < 0 ? -a : a;
        int v1 = b < 0 ? -b : b;
        int v2 = c < 0 ? -c : c;
        occCnt[v0]++; occCnt[v1]++; occCnt[v2]++;
        if (a > 0) posCnt[v0]++; else negCnt[v0]++;
        if (b > 0) posCnt[v1]++; else negCnt[v1]++;
        if (c > 0) posCnt[v2]++; else negCnt[v2]++;
    }

    // Build adjacency lists: variable -> list of clause indices (with duplicates)
    vector<vector<int>> occ(n + 1);
    for (int v = 1; v <= n; ++v) occ[v].reserve(occCnt[v]);
    for (int i = 0; i < m; ++i) {
        int a = clauses[i].l[0], b = clauses[i].l[1], c = clauses[i].l[2];
        occ[(a < 0 ? -a : a)].push_back(i);
        occ[(b < 0 ? -b : b)].push_back(i);
        occ[(c < 0 ? -c : c)].push_back(i);
    }

    RNG rng;

    // Initial assignment: majority
    vector<uint8_t> val(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] > negCnt[v]) val[v] = 1;
        else if (posCnt[v] < negCnt[v]) val[v] = 0;
        else val[v] = rng.nextBool();
    }

    // Helper lambdas
    auto lit_true = [&](int lit)->bool {
        int v = lit < 0 ? -lit : lit;
        bool x = val[v];
        return (lit > 0) ? x : (!x);
    };

    // sat count per clause
    vector<uint8_t> sat(m, 0);
    vector<int> breakcnt(n + 1, 0);
    vector<int> makecnt(n + 1, 0);

    vector<int> unsat_pos(m, -1);
    vector<int> unsat; unsat.reserve(m > 0 ? max(1, (int)(m / 8)) : 1);
    auto addUnsat = [&](int idx) {
        unsat_pos[idx] = (int)unsat.size();
        unsat.push_back(idx);
    };
    auto removeUnsat = [&](int idx) {
        int p = unsat_pos[idx];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        unsat_pos[last] = p;
        unsat.pop_back();
        unsat_pos[idx] = -1;
    };

    auto incMakeForClause = [&](const Clause &cl, int delta) {
        int va = cl.l[0] < 0 ? -cl.l[0] : cl.l[0];
        int vb = cl.l[1] < 0 ? -cl.l[1] : cl.l[1];
        int vc = cl.l[2] < 0 ? -cl.l[2] : cl.l[2];
        if (va == vb && vb == vc) {
            makecnt[va] += delta;
        } else if (va == vb) {
            makecnt[va] += delta;
            if (vc != va) makecnt[vc] += delta;
        } else if (va == vc) {
            makecnt[va] += delta;
            if (vb != va) makecnt[vb] += delta;
        } else if (vb == vc) {
            makecnt[vb] += delta;
            if (va != vb) makecnt[va] += delta;
        } else {
            makecnt[va] += delta;
            makecnt[vb] += delta;
            makecnt[vc] += delta;
        }
    };

    // Initialize sat counts, unsat list, break/make counts
    for (int i = 0; i < m; ++i) {
        int a = clauses[i].l[0];
        int b = clauses[i].l[1];
        int c = clauses[i].l[2];
        bool t0 = lit_true(a);
        bool t1 = lit_true(b);
        bool t2 = lit_true(c);
        int sc = (int)t0 + (int)t1 + (int)t2;
        sat[i] = (uint8_t)sc;
        if (sc == 0) {
            addUnsat(i);
            incMakeForClause(clauses[i], +1);
        } else if (sc == 1) {
            int uvar = t0 ? (a < 0 ? -a : a) : (t1 ? (b < 0 ? -b : b) : (c < 0 ? -c : c));
            breakcnt[uvar]++;
        }
    }

    // Helper arrays for flip processing
    vector<int> processedStamp(m, 0);
    int curStamp = 1;

    auto flipVar = [&](int v) {
        int stamp = ++curStamp;
        for (int idx = 0, sz = (int)occ[v].size(); idx < sz; ++idx) {
            int ci = occ[v][idx];
            if (processedStamp[ci] == stamp) continue;
            processedStamp[ci] = stamp;
            Clause &cl = clauses[ci];
            int l0 = cl.l[0], l1 = cl.l[1], l2 = cl.l[2];

            int v0 = (l0 < 0 ? -l0 : l0);
            int v1 = (l1 < 0 ? -l1 : l1);
            int v2 = (l2 < 0 ? -l2 : l2);

            bool t0 = (l0 > 0) ? (bool)val[v0] : !(bool)val[v0];
            bool t1 = (l1 > 0) ? (bool)val[v1] : !(bool)val[v1];
            bool t2 = (l2 > 0) ? (bool)val[v2] : !(bool)val[v2];

            int oldSat = (int)t0 + (int)t1 + (int)t2;

            bool nt0 = t0, nt1 = t1, nt2 = t2;
            if (v0 == v) nt0 = !t0;
            if (v1 == v) nt1 = !t1;
            if (v2 == v) nt2 = !t2;
            int newSat = (int)nt0 + (int)nt1 + (int)nt2;

            if (oldSat == 0 && newSat > 0) {
                if (unsat_pos[ci] != -1) removeUnsat(ci);
                incMakeForClause(cl, -1);
            } else if (oldSat > 0 && newSat == 0) {
                if (unsat_pos[ci] == -1) addUnsat(ci);
                incMakeForClause(cl, +1);
            }

            if (oldSat == 1) {
                int uvar = t0 ? v0 : (t1 ? v1 : v2);
                --breakcnt[uvar];
            }
            if (newSat == 1) {
                int uvar = nt0 ? v0 : (nt1 ? v1 : v2);
                ++breakcnt[uvar];
            }

            sat[ci] = (uint8_t)newSat;
        }
        val[v] ^= 1;
    };

    if (m > 0 && !unsat.empty()) {
        // Compute flip budget
        double avgDeg = (double)(3.0 * (double)m) / (double)max(1, n);
        int flipsLimit = 0;
        if (avgDeg > 0) {
            flipsLimit = (int)(30000000.0 / (3.0 * avgDeg) + 1.0);
            if (flipsLimit < 100) flipsLimit = 100;
            if (flipsLimit > 100000) flipsLimit = 100000;
        } else {
            flipsLimit = 1000;
        }
        int maxSteps = flipsLimit;
        double noise = 0.3;

        for (int step = 0; step < maxSteps; ++step) {
            if (unsat.empty()) break;
            int ci = unsat[rng.nextIntRange(0, (int)unsat.size() - 1)];
            Clause &cl = clauses[ci];
            int a = cl.l[0], b = cl.l[1], c = cl.l[2];
            int va = (a < 0 ? -a : a);
            int vb = (b < 0 ? -b : b);
            int vc = (c < 0 ? -c : c);

            // Build unique candidates
            int cand[3];
            int cc = 0;
            cand[cc++] = va;
            if (vb != va) cand[cc++] = vb;
            if (vc != va && vc != vb) cand[cc++] = vc;

            // Choose variable to flip
            int bestVar = cand[0];
            int bestDelta = makecnt[bestVar] - breakcnt[bestVar];
            for (int i = 1; i < cc; ++i) {
                int v = cand[i];
                int d = makecnt[v] - breakcnt[v];
                if (d > bestDelta) {
                    bestDelta = d; bestVar = v;
                } else if (d == bestDelta) {
                    if (rng.nextBool()) bestVar = v;
                }
            }

            if (bestDelta <= 0) {
                if (rng.nextDouble() < noise) {
                    bestVar = cand[rng.nextIntRange(0, cc - 1)];
                }
            }

            flipVar(bestVar);
        }
    }

    // Output
    // Print as 0/1 with spaces
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)val[i];
    }
    cout << '\n';
    return 0;
}