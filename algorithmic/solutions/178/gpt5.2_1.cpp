#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int cl;
    int lit; // signed literal as in input
};

struct Solver {
    int n, m;
    vector<array<int,3>> clauses;
    vector<vector<Occ>> occ; // 1..n
    vector<int> cnt;         // true literal count per clause
    vector<int> pos;         // position in unsat, -1 if satisfied
    vector<int> unsat;

    vector<int> mark, diff;
    int stamp = 1;

    uint64_t mask = 0;
    int satCount = 0;

    mt19937_64 rng;

    Solver(int n_, int m_) : n(n_), m(m_) {
        clauses.resize(m);
        occ.assign(n + 1, {});
        cnt.assign(m, 0);
        pos.assign(m, -1);
        unsat.clear();
        mark.assign(m, 0);
        diff.assign(m, 0);
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)this + 0x9e3779b97f4a7c15ULL;
        rng.seed(seed);
    }

    inline int rndInt(int bound) {
        return (int)(rng() % (uint64_t)bound);
    }

    inline bool varVal(int v) const {
        return (mask >> (v - 1)) & 1ULL;
    }

    inline bool litValSigned(int lit) const {
        int v = abs(lit);
        bool x = varVal(v);
        return (x == (lit > 0));
    }

    void initState(uint64_t startMask) {
        mask = startMask;
        unsat.clear();
        satCount = 0;
        fill(pos.begin(), pos.end(), -1);

        for (int i = 0; i < m; i++) {
            int c = 0;
            auto &cl = clauses[i];
            c += litValSigned(cl[0]) ? 1 : 0;
            c += litValSigned(cl[1]) ? 1 : 0;
            c += litValSigned(cl[2]) ? 1 : 0;
            cnt[i] = c;
            if (c == 0) {
                pos[i] = (int)unsat.size();
                unsat.push_back(i);
            } else {
                satCount++;
            }
        }
    }

    inline void unsatRemove(int cl) {
        int p = pos[cl];
        if (p < 0) return;
        int last = unsat.back();
        unsat[p] = last;
        pos[last] = p;
        unsat.pop_back();
        pos[cl] = -1;
    }

    inline void unsatAdd(int cl) {
        if (pos[cl] >= 0) return;
        pos[cl] = (int)unsat.size();
        unsat.push_back(cl);
    }

    void flipVar(int v) {
        mask ^= (1ULL << (v - 1));
        bool x = varVal(v);

        for (const auto &e : occ[v]) {
            int cl = e.cl;
            int old = cnt[cl];
            bool after = (x == (e.lit > 0)); // literal truth after flip
            int nw = old + (after ? 1 : -1);
            cnt[cl] = nw;

            if (old == 0 && nw > 0) {
                satCount++;
                unsatRemove(cl);
            } else if (old > 0 && nw == 0) {
                satCount--;
                unsatAdd(cl);
            }
        }
    }

    int deltaIfFlip(int v) {
        if (++stamp == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            stamp = 1;
        }

        vector<int> visited;
        visited.reserve(occ[v].size());

        bool x = varVal(v);

        for (const auto &e : occ[v]) {
            int cl = e.cl;
            if (mark[cl] != stamp) {
                mark[cl] = stamp;
                diff[cl] = 0;
                visited.push_back(cl);
            }
            bool before = (x == (e.lit > 0));
            diff[cl] += before ? -1 : +1;
        }

        int delta = 0;
        for (int cl : visited) {
            int old = cnt[cl];
            int nw = old + diff[cl];
            if (old == 0 && nw > 0) delta++;
            else if (old > 0 && nw == 0) delta--;
        }
        return delta;
    }

    int pickVarFromClause(int clIdx) {
        auto &cl = clauses[clIdx];

        int vars[3] = { abs(cl[0]), abs(cl[1]), abs(cl[2]) };
        int cand[3];
        int k = 0;
        for (int i = 0; i < 3; i++) {
            bool seen = false;
            for (int j = 0; j < k; j++) if (cand[j] == vars[i]) { seen = true; break; }
            if (!seen) cand[k++] = vars[i];
        }

        int bestV = cand[0];
        int bestD = INT_MIN;
        int ties[3];
        int t = 0;

        for (int i = 0; i < k; i++) {
            int v = cand[i];
            int d = deltaIfFlip(v);
            if (d > bestD) {
                bestD = d;
                t = 0;
                ties[t++] = v;
            } else if (d == bestD) {
                ties[t++] = v;
            }
        }
        bestV = ties[rndInt(t)];
        return bestV;
    }

    uint64_t randomMask() {
        uint64_t lim = (n == 64) ? ~0ULL : ((1ULL << n) - 1ULL);
        return rng() & lim;
    }

    void greedyImprove(uint64_t &bestMask, int &bestSat) {
        initState(bestMask);
        for (int iter = 0; iter < 80; iter++) {
            int bestD = 0;
            int bestV = -1;
            for (int v = 1; v <= n; v++) {
                int d = deltaIfFlip(v);
                if (d > bestD) {
                    bestD = d;
                    bestV = v;
                }
            }
            if (bestV < 0 || bestD <= 0) break;
            flipVar(bestV);
            if (satCount > bestSat) {
                bestSat = satCount;
                bestMask = mask;
                if (bestSat == m) break;
            }
        }
    }

    uint64_t solve(double timeLimitSec = 0.95) {
        if (m == 0) return 0;

        uint64_t bestMask = 0;
        int bestSat = -1;

        auto start = chrono::steady_clock::now();
        auto elapsed = [&]() -> double {
            return chrono::duration<double>(chrono::steady_clock::now() - start).count();
        };

        while (elapsed() < timeLimitSec) {
            uint64_t startMask = randomMask();
            initState(startMask);

            if (satCount > bestSat) {
                bestSat = satCount;
                bestMask = mask;
                if (bestSat == m) break;
            }

            int maxSteps = 12000 + 10 * m;
            for (int step = 0; step < maxSteps && elapsed() < timeLimitSec; step++) {
                if (satCount == m || unsat.empty()) break;

                int clIdx = unsat[rndInt((int)unsat.size())];

                int v;
                if ((rng() & 1ULL) == 0ULL) {
                    int pick = rndInt(3);
                    v = abs(clauses[clIdx][pick]);
                } else {
                    v = pickVarFromClause(clIdx);
                }

                flipVar(v);

                if (satCount > bestSat) {
                    bestSat = satCount;
                    bestMask = mask;
                    if (bestSat == m) break;
                }
            }

            if (bestSat == m) break;
        }

        greedyImprove(bestMask, bestSat);
        return bestMask;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    Solver solver(n, m);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        solver.clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; j++) {
            int lit = lits[j];
            int v = abs(lit);
            solver.occ[v].push_back({i, lit});
        }
    }

    uint64_t best = solver.solve(0.95);

    for (int i = 1; i <= n; i++) {
        int val = (best >> (i - 1)) & 1ULL;
        if (i > 1) cout << ' ';
        cout << val;
    }
    cout << '\n';
    return 0;
}