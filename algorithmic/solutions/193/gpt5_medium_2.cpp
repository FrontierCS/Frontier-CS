#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
    bool tautology;
    bool sameVar; // true if abs(a) == abs(b) and not tautology
};

struct RNG {
    uint64_t state;
    RNG() { state = chrono::high_resolution_clock::now().time_since_epoch().count(); }
    inline uint64_t next() {
        uint64_t x = state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        state = x;
        return x * 2685821657736338717ULL;
    }
    inline int randint(int l, int r) { return l + (int)(next() % (uint64_t)(r - l + 1)); }
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> occ;     // occ[v] = list of clause indices that include variable v (1-based)
vector<uint8_t> val;         // current assignment 0/1 for variables 1..n
vector<uint8_t> sat;         // clause satisfaction flags
vector<int> delta;           // gain in satisfied clauses if flipping variable v
long long satisfied = 0;     // number of satisfied clauses
RNG rng;

inline bool evalLit(int lit, const vector<uint8_t>& v) {
    int x = abs(lit);
    if (lit > 0) return v[x];
    else return !v[x];
}

inline bool clauseSat(const Clause& c, const vector<uint8_t>& v) {
    if (c.tautology) return true;
    return evalLit(c.a, v) || evalLit(c.b, v);
}

inline int contribForVarInClause(int idx, int v) {
    const Clause& c = clauses[idx];
    if (c.tautology) return 0;
    int a = c.a, b = c.b;
    int av = abs(a), bv = abs(b);
    if (av == bv) {
        // same variable clause (not tautology), effectively (lit ∨ lit) == lit
        // Contribution for this variable: +1 if currently false (would become true), -1 if currently true
        bool aTrue = evalLit(a, val);
        return aTrue ? -1 : +1;
    } else {
        if (av == v) {
            bool otherTrue = evalLit(b, val);
            if (otherTrue) return 0;
            bool selfTrue = evalLit(a, val);
            return selfTrue ? -1 : +1;
        } else { // bv == v
            bool otherTrue = evalLit(a, val);
            if (otherTrue) return 0;
            bool selfTrue = evalLit(b, val);
            return selfTrue ? -1 : +1;
        }
    }
}

void initState() {
    // Compute sat, satisfied, delta from current val
    fill(sat.begin(), sat.end(), 0);
    fill(delta.begin(), delta.end(), 0);
    satisfied = 0;
    for (int i = 0; i < m; ++i) {
        const Clause& c = clauses[i];
        if (c.tautology) {
            sat[i] = 1;
            ++satisfied;
            continue;
        }
        bool aTrue = evalLit(c.a, val);
        bool bTrue = evalLit(c.b, val);
        if (aTrue || bTrue) {
            sat[i] = 1;
            ++satisfied;
        }
        int av = abs(c.a), bv = abs(c.b);
        if (av == bv) {
            // single literal clause
            int v = av;
            delta[v] += (aTrue ? -1 : +1);
        } else {
            if (!bTrue) {
                int v1 = av;
                delta[v1] += (aTrue ? -1 : +1);
            }
            if (!aTrue) {
                int v2 = bv;
                delta[v2] += (bTrue ? -1 : +1);
            }
        }
    }
}

void flipVar(int v) {
    vector<int>& idxs = occ[v];
    int K = (int)idxs.size();
    // Store previous contributions for the other variable in each clause (if exists)
    vector<int> prevOtherVar(K, 0);
    vector<int> prevContrib(K, 0);
    for (int i = 0; i < K; ++i) {
        int idx = idxs[i];
        const Clause& c = clauses[idx];
        if (c.tautology) { prevOtherVar[i] = 0; prevContrib[i] = 0; continue; }
        int av = abs(c.a), bv = abs(c.b);
        if (av == bv) {
            prevOtherVar[i] = 0; prevContrib[i] = 0; // no other variable
        } else {
            int wVar = (av == v) ? bv : av;
            prevOtherVar[i] = wVar;
            prevContrib[i] = contribForVarInClause(idx, wVar);
        }
    }

    // Flip variable value
    val[v] ^= 1;
    // Update delta for v
    delta[v] = -delta[v];

    for (int i = 0; i < K; ++i) {
        int idx = idxs[i];
        const Clause& c = clauses[idx];

        bool before = sat[idx];
        bool after = clauseSat(c, val);
        if (before != after) {
            satisfied += after ? 1 : -1;
            sat[idx] = after;
        }

        int wVar = prevOtherVar[i];
        if (wVar != 0) {
            int newContrib = contribForVarInClause(idx, wVar);
            delta[wVar] += newContrib - prevContrib[i];
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m)) {
        return 0;
    }
    clauses.resize(m);
    occ.assign(n + 1, {});
    val.assign(n + 1, 0);
    sat.assign(m, 0);
    delta.assign(n + 1, 0);

    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        Clause c;
        c.a = a;
        c.b = b;
        c.tautology = (a == -b);
        c.sameVar = (!c.tautology && (abs(a) == abs(b)));
        clauses[i] = c;

        if (c.tautology) {
            // Always satisfied; do not add to occ or counts
            continue;
        }
        int av = abs(a), bv = abs(b);
        if (c.sameVar) {
            // add once
            occ[av].push_back(i);
            if (a > 0) posCnt[av]++; else negCnt[av]++;
        } else {
            occ[av].push_back(i);
            occ[bv].push_back(i);
            if (a > 0) posCnt[av]++; else negCnt[av]++;
            if (b > 0) posCnt[bv]++; else negCnt[bv]++;
        }
    }

    // Initial assignment: majority
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] >= negCnt[v]) val[v] = 1;
        else val[v] = 0;
    }

    initState();

    long long bestS = satisfied;
    vector<uint8_t> bestVal = val;

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 0.9;
    auto deadline = start + chrono::duration<double>(TIME_LIMIT_SEC);

    auto improve = [&](int maxSteps) {
        for (int step = 0; step < maxSteps; ++step) {
            if (chrono::steady_clock::now() > deadline) break;
            int bestVar = 1;
            int bestDelta = delta[1];
            int ties = 1;
            for (int v = 2; v <= n; ++v) {
                int d = delta[v];
                if (d > bestDelta) {
                    bestDelta = d;
                    bestVar = v;
                    ties = 1;
                } else if (d == bestDelta) {
                    ++ties;
                    if ((int)(rng.next() % (uint64_t)ties) == 0) {
                        bestVar = v;
                    }
                }
            }
            if (bestDelta <= 0) break;
            flipVar(bestVar);
            if (satisfied > bestS) {
                bestS = satisfied;
                bestVal = val;
                if (bestS == m) break;
            }
        }
    };

    improve(100000);

    // Random restarts while time allows
    for (int restart = 0; restart < 50 && chrono::steady_clock::now() <= deadline; ++restart) {
        // Random assignment
        for (int v = 1; v <= n; ++v) val[v] = (uint8_t)(rng.next() & 1ULL);
        initState();
        if (satisfied > bestS) {
            bestS = satisfied;
            bestVal = val;
        }
        improve(50000);
        if (bestS == m) break;
    }

    // Output best assignment
    for (int v = 1; v <= n; ++v) {
        if (v > 1) cout << ' ';
        cout << (int)bestVal[v];
    }
    cout << '\n';

    return 0;
}