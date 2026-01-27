#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];
    bool sgn[3];
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> C(m);
    vector<vector<pair<int,int>>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int vals[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = vals[j];
            bool sgn = lit > 0;
            int var = abs(lit);
            C[i].v[j] = var;
            C[i].sgn[j] = sgn;
            if (var >= 1 && var <= n)
                occ[var].push_back({i, j});
            if (sgn) posCnt[var]++; else negCnt[var]++;
        }
    }

    // Data structures for current assignment
    vector<int> x(n + 1, 0);
    vector<array<char,3>> litTrue(m);
    vector<int> satCnt(m, 0);
    vector<int> posInUnsat(m, -1), unsatList;
    int satisfied = 0;

    auto add_unsat = [&](int ci) {
        if (posInUnsat[ci] != -1) return;
        posInUnsat[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    };
    auto remove_unsat = [&](int ci) {
        int p = posInUnsat[ci];
        if (p == -1) return;
        int last = unsatList.back();
        unsatList[p] = last;
        posInUnsat[last] = p;
        unsatList.pop_back();
        posInUnsat[ci] = -1;
    };

    auto set_assignment = [&](const vector<int>& x0) {
        x = x0;
        satisfied = 0;
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            int sc = 0;
            for (int j = 0; j < 3; ++j) {
                int v = C[i].v[j];
                bool sgn = C[i].sgn[j];
                bool val = sgn ? (x[v] != 0) : (x[v] == 0);
                litTrue[i][j] = (char)val;
                sc += val;
            }
            satCnt[i] = sc;
            if (sc == 0) add_unsat(i);
            else satisfied++;
        }
    };

    // Initial assignment: majority
    vector<int> initX(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] + negCnt[v] == 0) {
            initX[v] = 0;
        } else {
            initX[v] = (posCnt[v] >= negCnt[v]) ? 1 : 0;
        }
    }
    set_assignment(initX);

    // Best solution tracking
    int bestS = satisfied;
    vector<int> bestX = x;

    // Structures for computing deltas
    vector<int> tmpDelta(m, 0), mark(m, 0);
    int tick = 1;

    auto predict_delta_var = [&](int v)->int {
        tick++;
        int delta = 0;
        vector<int> touched;
        for (auto [ci, pos] : occ[v]) {
            if (mark[ci] != tick) {
                mark[ci] = tick;
                tmpDelta[ci] = 0;
                touched.push_back(ci);
            }
            if (litTrue[ci][pos]) tmpDelta[ci] -= 1;
            else tmpDelta[ci] += 1;
        }
        for (int ci : touched) {
            int pre = satCnt[ci];
            int post = pre + tmpDelta[ci];
            if (pre == 0 && post > 0) delta += 1;
            else if (pre > 0 && post == 0) delta -= 1;
        }
        return delta;
    };

    auto flip_var = [&](int v) {
        tick++;
        vector<int> touched;
        for (auto [ci, pos] : occ[v]) {
            if (mark[ci] != tick) {
                mark[ci] = tick;
                tmpDelta[ci] = 0;
                touched.push_back(ci);
            }
            if (litTrue[ci][pos]) tmpDelta[ci] -= 1;
            else tmpDelta[ci] += 1;
        }
        for (int ci : touched) {
            int pre = satCnt[ci];
            int post = pre + tmpDelta[ci];
            if (pre == 0 && post > 0) {
                satisfied++;
                remove_unsat(ci);
            } else if (pre > 0 && post == 0) {
                satisfied--;
                add_unsat(ci);
            }
            satCnt[ci] = post;
        }
        x[v] ^= 1;
        for (auto [ci, pos] : occ[v]) {
            litTrue[ci][pos] ^= 1;
        }
    };

    // RNG setup
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed ^ (uint64_t)(uintptr_t)&seed);
    uniform_real_distribution<double> real01(0.0, 1.0);

    // Time budget
    auto start = chrono::steady_clock::now();
    // Use a conservative time budget
    const double timeBudgetSec = 0.9;
    auto deadline = start + chrono::duration<double>(timeBudgetSec);

    // WalkSAT parameters
    const double noiseProb = 0.3;
    const int noImproveLimit = 20000;

    auto random_biased_assignment = [&]() -> vector<int> {
        vector<int> rx(n + 1);
        for (int v = 1; v <= n; ++v) {
            int total = posCnt[v] + negCnt[v];
            if (total == 0) {
                rx[v] = (rng() & 1);
            } else {
                double p = (double)posCnt[v] / (double)total;
                rx[v] = (real01(rng) < p) ? 1 : 0;
            }
        }
        return rx;
    };

    // Local search with restarts
    while (chrono::steady_clock::now() < deadline) {
        int stepsNoImprove = 0;
        while (chrono::steady_clock::now() < deadline) {
            if (unsatList.empty()) break;
            int ci = unsatList[rng() % unsatList.size()];
            // Unique candidate variables from the clause
            int cand[3];
            int candCnt = 0;
            bool used[51] = {false};
            for (int j = 0; j < 3; ++j) {
                int v = C[ci].v[j];
                if (!used[v]) {
                    used[v] = true;
                    cand[candCnt++] = v;
                }
            }
            int pickVar;
            if (real01(rng) < noiseProb) {
                pickVar = cand[rng() % candCnt];
            } else {
                int bestDelta = INT_MIN;
                int bestVars[3];
                int bestCnt = 0;
                for (int k = 0; k < candCnt; ++k) {
                    int v = cand[k];
                    int d = predict_delta_var(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        bestCnt = 0;
                        bestVars[bestCnt++] = v;
                    } else if (d == bestDelta) {
                        bestVars[bestCnt++] = v;
                    }
                }
                pickVar = bestVars[rng() % bestCnt];
            }
            flip_var(pickVar);

            if (satisfied > bestS) {
                bestS = satisfied;
                bestX = x;
                stepsNoImprove = 0;
            } else {
                stepsNoImprove++;
                if (stepsNoImprove >= noImproveLimit) break;
            }
        }
        if (unsatList.empty()) break;
        // Restart with biased random assignment
        vector<int> rx = random_biased_assignment();
        set_assignment(rx);
        if (satisfied > bestS) {
            bestS = satisfied;
            bestX = x;
        }
    }

    // Output best found assignment (or current if better)
    if (satisfied < bestS) x = bestX;
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (x[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}