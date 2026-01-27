#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<array<int,3>> clauses;               // literals as input (signed ints)
    vector<vector<int>> posOcc, negOcc;         // clause indices per variable occurrence
    vector<int> assign, bestAssign;             // current and best assignment (0/1)
    vector<int> sats;                           // number of satisfied literals per clause
    vector<int> unsatList, posInUnsat;          // unsatisfied clauses list and positions
    int satisfiedCount = 0;
    int bestSatisfied = -1;

    mt19937_64 rng;
    uniform_real_distribution<double> U01{0.0, 1.0};

    Solver(int n_, int m_) : n(n_), m(m_), clauses(m_), posOcc(n_), negOcc(n_), assign(n_,0), bestAssign(n_,0),
                             sats(m_,0), posInUnsat(m_, -1) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count()
                        ^ (uint64_t)(uintptr_t(new int));
        rng.seed(seed);
    }

    inline double rand01() { return U01(rng); }
    inline int randint(int l, int r) { // inclusive
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    }

    void addUnsat(int ci) {
        if (posInUnsat[ci] != -1) return;
        posInUnsat[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    }

    void removeUnsat(int ci) {
        int pos = posInUnsat[ci];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        posInUnsat[last] = pos;
        unsatList.pop_back();
        posInUnsat[ci] = -1;
    }

    void initStructures() {
        // Build occurrence lists
        for (int i = 0; i < m; ++i) {
            for (int k = 0; k < 3; ++k) {
                int lit = clauses[i][k];
                int v = abs(lit) - 1;
                if (lit > 0) posOcc[v].push_back(i);
                else negOcc[v].push_back(i);
            }
        }
    }

    void randomInitialAssignment(bool polarityBias = true) {
        // Polarity heuristic with some noise
        if (polarityBias) {
            for (int v = 0; v < n; ++v) {
                int p = (int)posOcc[v].size();
                int q = (int)negOcc[v].size();
                if (p > q) assign[v] = 1;
                else if (p < q) assign[v] = 0;
                else assign[v] = randint(0,1);
                // small noise
                if (rand01() < 0.1) assign[v] ^= 1;
            }
        } else {
            for (int v = 0; v < n; ++v) assign[v] = randint(0,1);
        }

        // Compute sats and unsat list
        fill(sats.begin(), sats.end(), 0);
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        satisfiedCount = 0;

        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            for (int k = 0; k < 3; ++k) {
                int lit = clauses[i][k];
                int v = abs(lit) - 1;
                int val = assign[v];
                bool truth = (lit > 0) ? (val == 1) : (val == 0);
                if (truth) ++cnt;
            }
            sats[i] = cnt;
            if (cnt > 0) ++satisfiedCount;
            else addUnsat(i);
        }
    }

    // Compute break and make for a variable v; delta = make - break
    inline void computeMakeBreak(int v, int &makeCnt, int &breakCnt) {
        makeCnt = 0; breakCnt = 0;
        int val = assign[v];
        if (val == 1) {
            // positive literals currently true -> possible break if clause has exactly 1 true literal
            for (int ci : posOcc[v]) if (sats[ci] == 1) ++breakCnt;
            // negative literals currently false -> possible make if clause currently unsatisfied
            for (int ci : negOcc[v]) if (sats[ci] == 0) ++makeCnt;
        } else {
            // positive literals currently false -> possible make if clause currently unsatisfied
            for (int ci : posOcc[v]) if (sats[ci] == 0) ++makeCnt;
            // negative literals currently true -> possible break if clause has exactly 1 true literal
            for (int ci : negOcc[v]) if (sats[ci] == 1) ++breakCnt;
        }
    }

    inline int computeDelta(int v) {
        int makeCnt, breakCnt;
        computeMakeBreak(v, makeCnt, breakCnt);
        return makeCnt - breakCnt;
    }

    inline void flipVar(int v) {
        int oldVal = assign[v];
        int newVal = 1 - oldVal;
        assign[v] = newVal;

        if (oldVal == 1) {
            // pos literals go from true->false
            for (int ci : posOcc[v]) {
                int x = --sats[ci];
                if (x == 0) {
                    --satisfiedCount;
                    addUnsat(ci);
                }
            }
            // neg literals go from false->true
            for (int ci : negOcc[v]) {
                int x = ++sats[ci];
                if (x == 1) {
                    ++satisfiedCount;
                    removeUnsat(ci);
                }
            }
        } else {
            // oldVal == 0
            // pos literals go from false->true
            for (int ci : posOcc[v]) {
                int x = ++sats[ci];
                if (x == 1) {
                    ++satisfiedCount;
                    removeUnsat(ci);
                }
            }
            // neg literals go from true->false
            for (int ci : negOcc[v]) {
                int x = --sats[ci];
                if (x == 0) {
                    --satisfiedCount;
                    addUnsat(ci);
                }
            }
        }
    }

    void run(double timeLimitSeconds) {
        if (m == 0) {
            bestAssign.assign(n, 0);
            bestSatisfied = 0;
            return;
        }
        initStructures();

        auto tStart = chrono::steady_clock::now();
        auto elapsed = [&]() -> double {
            auto now = chrono::steady_clock::now();
            return chrono::duration_cast<chrono::duration<double>>(now - tStart).count();
        };

        // Parameters
        const double pNoise = 0.35;           // probability to choose random variable in a chosen unsatisfied clause (WalkSAT noise)
        const int maxFlipsPerRestart = 200000;
        const int checkTimeEvery = 512;

        bestSatisfied = -1;
        bestAssign.assign(n, 0);

        int restarts = 0;
        while (elapsed() < timeLimitSeconds) {
            bool usePolarity = (rand01() < 0.7);
            randomInitialAssignment(usePolarity);

            if (satisfiedCount > bestSatisfied) {
                bestSatisfied = satisfiedCount;
                bestAssign = assign;
                if (bestSatisfied == m) break;
            }

            int iter = 0;
            int noImprovement = 0;
            while (iter < maxFlipsPerRestart) {
                if (satisfiedCount == m) {
                    bestSatisfied = satisfiedCount;
                    bestAssign = assign;
                    break;
                }

                // WalkSAT step: choose a random unsatisfied clause
                int ci = unsatList[randint(0, (int)unsatList.size() - 1)];

                // Gather its three variables
                int vars[3];
                for (int k = 0; k < 3; ++k) {
                    vars[k] = abs(clauses[ci][k]) - 1;
                }

                int chosenVar;
                if (rand01() < pNoise) {
                    // pick random variable from clause
                    chosenVar = vars[randint(0,2)];
                } else {
                    // choose variable with minimal break; tie broken randomly
                    int bestBreak = INT_MAX;
                    int candidates[3];
                    int candCnt = 0;
                    for (int t = 0; t < 3; ++t) {
                        int v = vars[t];
                        int makeCnt, breakCnt;
                        computeMakeBreak(v, makeCnt, breakCnt);
                        if (breakCnt < bestBreak) {
                            bestBreak = breakCnt;
                            candidates[0] = v;
                            candCnt = 1;
                        } else if (breakCnt == bestBreak) {
                            candidates[candCnt++] = v;
                        }
                    }
                    chosenVar = candidates[randint(0, candCnt - 1)];
                }

                int before = satisfiedCount;
                flipVar(chosenVar);
                int after = satisfiedCount;

                if (after > bestSatisfied) {
                    bestSatisfied = after;
                    bestAssign = assign;
                    noImprovement = 0;
                    if (bestSatisfied == m) break;
                } else {
                    noImprovement++;
                }

                ++iter;
                if ((iter & (checkTimeEvery - 1)) == 0) {
                    if (elapsed() >= timeLimitSeconds) break;
                    // occasional diversification if stuck
                    if (noImprovement > 4000) {
                        // random flips to escape local minima
                        int kicks = min(10, n);
                        for (int k = 0; k < kicks; ++k) {
                            int v = randint(0, n-1);
                            flipVar(v);
                        }
                        noImprovement = 0;
                    }
                }
            }
            ++restarts;
            if (elapsed() >= timeLimitSeconds) break;
        }

        // If we didn't find any (shouldn't happen), ensure some assignment
        if (bestSatisfied < 0) {
            bestAssign.assign(n, 0);
            bestSatisfied = 0;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    Solver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        solver.clauses[i] = {a, b, c};
    }

    // Adaptive time limit: try to use around 0.9 seconds
    double timeLimit = 0.9;
    solver.run(timeLimit);

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << solver.bestAssign[i];
    }
    cout << '\n';
    return 0;
}