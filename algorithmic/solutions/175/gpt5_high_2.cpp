#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline bool readInt(int &out) {
        char c; int sgn = 1; int x = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) { c = getChar(); if (!c) return false; }
        if (c == '-') { sgn = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x*10 + (c - '0');
        out = x * sgn;
        return true;
    }
};

struct Clause {
    int lit[3];
    unsigned char sc;   // satisfied literal count (0..3)
    signed char ui;     // index of unique satisfied literal if sc==1 else -1
    unsigned char pad0;
    unsigned char pad1;
};

static inline int litVar(int l) { return l > 0 ? l : -l; }
static inline bool litTrue(int l, const vector<unsigned char> &A) {
    int v = l > 0 ? l : -l;
    return l > 0 ? (A[v] != 0) : (A[v] == 0);
}

struct RNG {
    uint64_t s;
    RNG(uint64_t seed=0x9e3779b97f4a7c15ULL) : s(seed) {
        if (s == 0) s = 0x9e3779b97f4a7c15ULL;
    }
    inline uint64_t next() {
        // splitmix64
        uint64_t z = (s += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t next32() { return (uint32_t)next(); }
    inline uint64_t next(uint64_t mod) { return next() % mod; }
    inline int nextInt(int l, int r) { // inclusive
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<Clause> clauses(m);
    vector<vector<uint32_t>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        clauses[i].lit[2] = c;
        clauses[i].sc = 0;
        clauses[i].ui = -1;
        // Build occurrence lists and pos/neg counts
        int ls[3] = {a,b,c};
        for (int j = 0; j < 3; ++j) {
            int v = ls[j] > 0 ? ls[j] : -ls[j];
            if (ls[j] > 0) ++posCnt[v]; else ++negCnt[v];
            occ[v].push_back(((uint32_t)i << 2) | (uint32_t)j);
        }
    }

    vector<unsigned char> A(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        A[v] = (unsigned char)(posCnt[v] >= negCnt[v]);
    }

    vector<int> U0(n + 1, 0); // number of unsatisfied clauses containing v
    vector<int> U1(n + 1, 0); // number of clauses uniquely satisfied by v

    vector<int> unsatPos(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    // Initialize clause satisfaction and counts
    for (int i = 0; i < m; ++i) {
        Clause &cl = clauses[i];
        bool t0 = litTrue(cl.lit[0], A);
        bool t1 = litTrue(cl.lit[1], A);
        bool t2 = litTrue(cl.lit[2], A);
        int sc = (int)t0 + (int)t1 + (int)t2;
        cl.sc = (unsigned char)sc;
        if (sc == 0) {
            cl.ui = -1;
            unsatPos[i] = (int)unsatList.size();
            unsatList.push_back(i);
            for (int j = 0; j < 3; ++j) {
                int v = litVar(cl.lit[j]);
                ++U0[v];
            }
        } else if (sc == 1) {
            int idx = t0 ? 0 : (t1 ? 1 : 2);
            cl.ui = (signed char)idx;
            int v = litVar(cl.lit[idx]);
            ++U1[v];
        } else {
            cl.ui = -1;
        }
    }

    RNG rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Best assignment tracking
    int bestUnsat = (int)unsatList.size();
    vector<unsigned char> bestA = A;

    // Time budget for search in milliseconds
    auto startTime = chrono::steady_clock::now();
    const int timeBudgetMs = 1400; // conservative
    auto timeLimit = startTime + chrono::milliseconds(timeBudgetMs);

    // Helper lambdas for unsat list management
    auto addUnsat = [&](int ci) {
        if (unsatPos[ci] == -1) {
            unsatPos[ci] = (int)unsatList.size();
            unsatList.push_back(ci);
        }
    };
    auto removeUnsat = [&](int ci) {
        int pos = unsatPos[ci];
        if (pos != -1) {
            int last = unsatList.back();
            unsatList[pos] = last;
            unsatPos[last] = pos;
            unsatList.pop_back();
            unsatPos[ci] = -1;
        }
    };

    // For robust updates (handle potential duplicate literals), ensure each clause is processed once per flip
    vector<uint32_t> lastVisit(m, 0);
    uint32_t visitToken = 1;

    auto flipVar = [&](int v) {
        // Toggle assignment
        A[v] ^= 1;
        // Process each clause containing v once
        ++visitToken;
        if (visitToken == 0) { // unlikely wrap-around safeguard
            fill(lastVisit.begin(), lastVisit.end(), 0);
            visitToken = 1;
        }
        for (uint32_t packed : occ[v]) {
            int ci = (int)(packed >> 2);
            if (lastVisit[ci] == visitToken) continue;
            lastVisit[ci] = visitToken;

            Clause &cl = clauses[ci];
            int oldSC = (int)cl.sc;
            int oldUI = (int)cl.ui;

            bool nt[3];
            int newSC = 0;
            for (int j = 0; j < 3; ++j) {
                int lj = cl.lit[j];
                int u = litVar(lj);
                if (u == v) {
                    // literal truth after flip
                    nt[j] = (lj > 0 ? (A[v] != 0) : (A[v] == 0));
                } else {
                    nt[j] = litTrue(lj, A);
                }
                newSC += nt[j] ? 1 : 0;
            }
            int newUI = -1;
            if (newSC == 1) {
                newUI = nt[0] ? 0 : (nt[1] ? 1 : 2);
            }

            // Unsatisfied transitions
            if (oldSC == 0 && newSC > 0) {
                removeUnsat(ci);
                for (int j = 0; j < 3; ++j) {
                    int u = litVar(cl.lit[j]);
                    --U0[u];
                }
            } else if (oldSC > 0 && newSC == 0) {
                addUnsat(ci);
                for (int j = 0; j < 3; ++j) {
                    int u = litVar(cl.lit[j]);
                    ++U0[u];
                }
            }

            // Unique satisfied transitions
            if (oldSC == 1 && oldUI >= 0) {
                int u = litVar(cl.lit[oldUI]);
                --U1[u];
            }
            if (newSC == 1 && newUI >= 0) {
                int u = litVar(cl.lit[newUI]);
                ++U1[u];
            }

            cl.sc = (unsigned char)newSC;
            cl.ui = (signed char)newUI;
        }
    };

    // WalkSAT-like local search
    const uint32_t noiseThreshold = (uint32_t)(0.4 * 4294967295.0); // ~0.4
    const int maxSteps = max(10000, min(500000, m > 0 ? m : 10000)); // rough bound

    int steps = 0;
    while (steps < maxSteps) {
        if (unsatList.empty()) break;
        if (chrono::steady_clock::now() > timeLimit) break;

        int ci = unsatList[(size_t)(rng.next() % (uint64_t)unsatList.size())];
        Clause &cl = clauses[ci];

        int chosenVar;
        if (rng.next32() < noiseThreshold) {
            int j = (int)(rng.next() % 3ULL);
            chosenVar = litVar(cl.lit[j]);
        } else {
            int bestVar = litVar(cl.lit[0]);
            int bestGain = U0[bestVar] - U1[bestVar];
            int j1Var = litVar(cl.lit[1]);
            int j1Gain = U0[j1Var] - U1[j1Var];
            if (j1Gain > bestGain || (j1Gain == bestGain && (rng.next32() & 1))) {
                bestVar = j1Var;
                bestGain = j1Gain;
            }
            int j2Var = litVar(cl.lit[2]);
            int j2Gain = U0[j2Var] - U1[j2Var];
            if (j2Gain > bestGain || (j2Gain == bestGain && (rng.next32() & 1))) {
                bestVar = j2Var;
                bestGain = j2Gain;
            }
            chosenVar = bestVar;
        }

        flipVar(chosenVar);
        ++steps;

        int curUnsat = (int)unsatList.size();
        if (curUnsat < bestUnsat) {
            bestUnsat = curUnsat;
            bestA = A;
            if (bestUnsat == 0) break;
        }
    }

    // Output best assignment found
    // If m == 0, any assignment is fine; we output zeros by default
    const vector<unsigned char> &outA = (m == 0) ? A : bestA;
    for (int v = 1; v <= n; ++v) {
        if (v > 1) cout << ' ';
        cout << (outA[v] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}