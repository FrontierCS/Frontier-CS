#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t state;
    RNG() { state = chrono::high_resolution_clock::now().time_since_epoch().count(); }
    inline uint64_t next() {
        state ^= state << 7;
        state ^= state >> 9;
        return state;
    }
    inline int randint(int l, int r) { return l + (int)(next() % (uint64_t)(r - l + 1)); }
    inline double rand01() { return (next() >> 11) * (1.0 / (1ull << 53)); }
};

static inline int popcnt3(unsigned char x) {
    static const int pc[8] = {0,1,1,2,1,2,2,3};
    return pc[x & 7];
}

struct Clause {
    int v[3];
    unsigned char sgn[3];       // 1 for positive literal, 0 for negated
    unsigned char satMask = 0;  // which literals currently satisfied (3 bits)
    unsigned char sc = 0;       // number of satisfied literals
    int uniqCount = 0;
    int uniqVars[3];            // distinct variables in this clause
    unsigned char occMask[3];   // bitmask of positions for each uniq var
    unsigned char occCount[3];  // popcount of occMask for each uniq var
};

int n, m;
vector<Clause> cls;
vector<vector<pair<int, unsigned char>>> occ; // per variable: list of (clause index, occMask in that clause)
vector<int> makeCnt, breakCnt, deltaCnt;
vector<int> posCount, negCount;
vector<unsigned char> val, bestVal;
vector<int> posInUnsat; // -1 if not unsatisfied; else index in unsatList
vector<int> unsatList;
int satisfiedClauses = 0, bestSatisfied = 0;

RNG rng;

inline void addUnsat(int ci) {
    if (posInUnsat[ci] != -1) return;
    posInUnsat[ci] = (int)unsatList.size();
    unsatList.push_back(ci);
}
inline void removeUnsat(int ci) {
    int pos = posInUnsat[ci];
    if (pos == -1) return;
    int last = unsatList.back();
    unsatList[pos] = last;
    posInUnsat[last] = pos;
    unsatList.pop_back();
    posInUnsat[ci] = -1;
}

void rebuildAll() {
    int M = m;
    fill(makeCnt.begin(), makeCnt.end(), 0);
    fill(breakCnt.begin(), breakCnt.end(), 0);
    fill(deltaCnt.begin(), deltaCnt.end(), 0);
    fill(posInUnsat.begin(), posInUnsat.end(), -1);
    unsatList.clear();

    for (int ci = 0; ci < m; ++ci) {
        Clause &c = cls[ci];
        unsigned char mask = 0;
        for (int j = 0; j < 3; ++j) {
            if (val[c.v[j]] == c.sgn[j]) mask |= (1u << j);
        }
        c.satMask = mask;
        c.sc = (unsigned char)popcnt3(mask);
        if (c.sc == 0) {
            addUnsat(ci);
            for (int u = 0; u < c.uniqCount; ++u) {
                makeCnt[c.uniqVars[u]] += 1;
            }
        } else if (c.sc == 1) {
            for (int u = 0; u < c.uniqCount; ++u) {
                if (c.occCount[u] == 1 && (c.satMask & c.occMask[u])) {
                    breakCnt[c.uniqVars[u]] += 1;
                }
            }
        }
    }
    for (int v = 1; v <= n; ++v) {
        deltaCnt[v] = makeCnt[v] - breakCnt[v];
    }
    satisfiedClauses = m - (int)unsatList.size();
}

void flipVar(int v) {
    val[v] ^= 1u;
    for (auto &p : occ[v]) {
        int ci = p.first;
        unsigned char vMask = p.second;
        Clause &c = cls[ci];
        unsigned char oldMask = c.satMask;
        int oldSc = c.sc;

        // Remove old contributions
        if (oldSc == 0) {
            for (int u = 0; u < c.uniqCount; ++u) {
                makeCnt[c.uniqVars[u]] -= 1;
            }
        } else if (oldSc == 1) {
            for (int u = 0; u < c.uniqCount; ++u) {
                if (c.occCount[u] == 1 && (oldMask & c.occMask[u])) {
                    breakCnt[c.uniqVars[u]] -= 1;
                }
            }
        }

        // Update sat mask and count
        int s_in_mask = popcnt3((unsigned char)(oldMask & vMask));
        int bits = popcnt3(vMask);
        unsigned char newMask = (unsigned char)(oldMask ^ vMask);
        int newSc = oldSc + bits - 2 * s_in_mask;

        // Update unsatisfied set and satisfied count
        if (oldSc == 0 && newSc > 0) {
            removeUnsat(ci);
            satisfiedClauses++;
        } else if (oldSc > 0 && newSc == 0) {
            addUnsat(ci);
            satisfiedClauses--;
        }

        c.satMask = newMask;
        c.sc = (unsigned char)newSc;

        // Add new contributions
        if (newSc == 0) {
            for (int u = 0; u < c.uniqCount; ++u) {
                makeCnt[c.uniqVars[u]] += 1;
            }
        } else if (newSc == 1) {
            for (int u = 0; u < c.uniqCount; ++u) {
                if (c.occCount[u] == 1 && (newMask & c.occMask[u])) {
                    breakCnt[c.uniqVars[u]] += 1;
                }
            }
        }

        // Update deltas for variables in this clause
        for (int u = 0; u < c.uniqCount; ++u) {
            int varId = c.uniqVars[u];
            deltaCnt[varId] = makeCnt[varId] - breakCnt[varId];
        }
    }
}

int pickFromUnsatClause() {
    if (unsatList.empty()) return rng.randint(1, n); // fallback
    int ci = unsatList[rng.randint(0, (int)unsatList.size() - 1)];
    Clause &c = cls[ci];
    // Collect unique vars in the clause
    vector<int> zeros;
    int bestVar = c.uniqVars[0];
    int bestBreak = INT_MAX;
    int bestDelta = INT_MIN;
    for (int u = 0; u < c.uniqCount; ++u) {
        int varId = c.uniqVars[u];
        int b = breakCnt[varId];
        if (b == 0) zeros.push_back(varId);
    }
    if (!zeros.empty()) {
        return zeros[rng.randint(0, (int)zeros.size() - 1)];
    }
    for (int u = 0; u < c.uniqCount; ++u) {
        int varId = c.uniqVars[u];
        int b = breakCnt[varId];
        int d = deltaCnt[varId];
        if (b < bestBreak || (b == bestBreak && d > bestDelta) || (b == bestBreak && d == bestDelta && rng.next() & 1)) {
            bestBreak = b;
            bestDelta = d;
            bestVar = varId;
        }
    }
    return (bestVar >= 1 && bestVar <= n) ? bestVar : rng.randint(1, n);
}

int pickGreedy() {
    int bestVar = 1;
    int bestD = INT_MIN;
    for (int v = 1; v <= n; ++v) {
        int d = deltaCnt[v];
        if (d > bestD || (d == bestD && (rng.next() & 1))) {
            bestD = d;
            bestVar = v;
        }
    }
    return bestVar;
}

void randomRestart() {
    for (int v = 1; v <= n; ++v) {
        if (posCount[v] > negCount[v]) val[v] = 1;
        else if (posCount[v] < negCount[v]) val[v] = 0;
        else val[v] = (unsigned char)(rng.next() & 1);
    }
    rebuildAll();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) {
        return 0;
    }

    cls.resize(m);
    occ.assign(n + 1, {});
    posCount.assign(n + 1, 0);
    negCount.assign(n + 1, 0);
    makeCnt.assign(n + 1, 0);
    breakCnt.assign(n + 1, 0);
    deltaCnt.assign(n + 1, 0);
    val.assign(n + 1, 0);
    bestVal.assign(n + 1, 0);
    posInUnsat.assign(m, -1);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        Clause cl;
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            int var = abs(x);
            unsigned char sgn = (x > 0) ? 1 : 0;
            cl.v[j] = var;
            cl.sgn[j] = sgn;
            if (sgn) posCount[var]++; else negCount[var]++;
        }
        // build uniq vars and masks
        int uniqCount = 0;
        for (int j = 0; j < 3; ++j) {
            int var = cl.v[j];
            int idx = -1;
            for (int k = 0; k < uniqCount; ++k) {
                if (cl.uniqVars[k] == var) { idx = k; break; }
            }
            if (idx == -1) {
                idx = uniqCount++;
                cl.uniqVars[idx] = var;
                cl.occMask[idx] = 0;
            }
            cl.occMask[idx] = (unsigned char)(cl.occMask[idx] | (1u << j));
        }
        cl.uniqCount = uniqCount;
        for (int k = 0; k < uniqCount; ++k) {
            cl.occCount[k] = (unsigned char)popcnt3(cl.occMask[k]);
        }
        cls[i] = cl;
    }

    // Build occurrences
    for (int ci = 0; ci < m; ++ci) {
        Clause &c = cls[ci];
        for (int u = 0; u < c.uniqCount; ++u) {
            int varId = c.uniqVars[u];
            occ[varId].push_back({ci, c.occMask[u]});
        }
    }

    // Initial assignment
    for (int v = 1; v <= n; ++v) {
        if (posCount[v] > negCount[v]) val[v] = 1;
        else if (posCount[v] < negCount[v]) val[v] = 0;
        else val[v] = (unsigned char)(rng.next() & 1);
    }

    rebuildAll();
    bestSatisfied = satisfiedClauses;
    bestVal = val;

    auto start = chrono::steady_clock::now();
    const double timeLimitSec = 0.9;
    auto deadline = start + chrono::duration<double>(timeLimitSec);

    int iter = 0;
    int lastImproveIter = 0;
    const double walkProb = 0.45;

    while (chrono::steady_clock::now() < deadline) {
        if (satisfiedClauses == m) break;
        int vflip;
        if (!unsatList.empty() && rng.rand01() < walkProb) {
            vflip = pickFromUnsatClause();
        } else {
            vflip = pickGreedy();
            if (deltaCnt[vflip] <= 0 && !unsatList.empty()) {
                vflip = pickFromUnsatClause();
            }
        }
        flipVar(vflip);
        ++iter;

        if (satisfiedClauses > bestSatisfied) {
            bestSatisfied = satisfiedClauses;
            bestVal = val;
            lastImproveIter = iter;
            if (bestSatisfied == m) break;
        }

        if (iter - lastImproveIter > 10000) {
            randomRestart();
            if (satisfiedClauses > bestSatisfied) {
                bestSatisfied = satisfiedClauses;
                bestVal = val;
                lastImproveIter = iter;
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}