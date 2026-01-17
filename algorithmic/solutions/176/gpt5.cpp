#include <bits/stdc++.h>
using namespace std;

struct Occ { int c, pos; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<array<int,3>> clauses(m);
    vector<vector<Occ>> occ(n);
    vector<int> posCnt(n,0), negCnt(n,0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int v = abs(lit) - 1;
            occ[v].push_back({i, j});
            if (lit > 0) posCnt[v]++; else negCnt[v]++;
        }
    }

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 0.95; // seconds

    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    auto time_elapsed = [&]() -> double {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    vector<char> bestAssign(n, 0), assign(n, 0);
    for (int v = 0; v < n; ++v) {
        if (posCnt[v] > negCnt[v]) assign[v] = 1;
        else if (posCnt[v] < negCnt[v]) assign[v] = 0;
        else assign[v] = (rng() & 1);
    }
    bestAssign = assign;

    vector<int> satcnt(m, 0);
    vector<int> unsat, posInUnsat(m, -1);
    unsat.reserve(m);

    auto isLitSat = [&](int lit) -> bool {
        int v = abs(lit) - 1;
        return (lit > 0) ? assign[v] : !assign[v];
    };

    auto build_state = [&]() {
        fill(satcnt.begin(), satcnt.end(), 0);
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            int s = 0;
            auto &cl = clauses[i];
            if (isLitSat(cl[0])) ++s;
            if (isLitSat(cl[1])) ++s;
            if (isLitSat(cl[2])) ++s;
            satcnt[i] = s;
            if (s == 0) {
                posInUnsat[i] = (int)unsat.size();
                unsat.push_back(i);
            }
        }
    };

    auto add_unsat = [&](int c) {
        if (posInUnsat[c] == -1) {
            posInUnsat[c] = (int)unsat.size();
            unsat.push_back(c);
        }
    };

    auto remove_unsat = [&](int c) {
        int pos = posInUnsat[c];
        if (pos == -1) return;
        int lastc = unsat.back();
        unsat[pos] = lastc;
        posInUnsat[lastc] = pos;
        unsat.pop_back();
        posInUnsat[c] = -1;
    };

    auto flipVar = [&](int v) {
        char oldVal = assign[v];
        char newVal = oldVal ^ 1;
        assign[v] = newVal;
        for (const auto &oc : occ[v]) {
            int ci = oc.c;
            int lit = clauses[ci][oc.pos];
            bool before = (lit > 0) ? oldVal : !oldVal;
            bool after  = (lit > 0) ? newVal : !newVal;
            if (before && !after) {
                int sc = --satcnt[ci];
                if (sc == 0) add_unsat(ci);
            } else if (!before && after) {
                int sc = ++satcnt[ci];
                if (sc == 1) remove_unsat(ci);
            }
        }
    };

    auto breakCount = [&](int v) -> int {
        int br = 0;
        for (const auto &oc : occ[v]) {
            int ci = oc.c;
            if (satcnt[ci] == 1) {
                int lit = clauses[ci][oc.pos];
                char val = assign[v];
                bool sat = (lit > 0) ? val : !val;
                if (sat) ++br;
            }
        }
        return br;
    };

    int bestUnsat = m + 1;

    // Initial evaluation
    build_state();
    bestUnsat = (int)unsat.size();
    bestAssign = assign;
    if (bestUnsat == 0) {
        for (int i = 0; i < n; ++i) {
            cout << (int)assign[i] << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }

    const double noiseProb = 0.5;

    int restart = 0;
    while (time_elapsed() < TIME_LIMIT) {
        // Restart strategy: first restart uses heuristic assignment; subsequent restarts randomize heavily
        if (restart == 0) {
            assign = bestAssign; // Start from best known so far (heuristic)
        } else {
            for (int v = 0; v < n; ++v) assign[v] = (rng() & 1);
        }
        build_state();

        long long maxFlips = max(10000LL, 20LL * m);
        for (long long step = 0; step < maxFlips; ++step) {
            if (unsat.empty()) {
                for (int i = 0; i < n; ++i) {
                    cout << (int)assign[i] << (i + 1 == n ? '\n' : ' ');
                }
                return 0;
            }
            int ci = unsat[rng() % unsat.size()];
            auto &cl = clauses[ci];
            int chosenVar;
            if (uniform_real_distribution<double>(0.0, 1.0)(rng) < noiseProb) {
                int lit = cl[rng() % 3];
                chosenVar = abs(lit) - 1;
            } else {
                int bestVar = -1;
                int bestBr = INT_MAX;
                int order[3] = {0,1,2};
                // Randomize tie-breaking order
                if ((rng() & 1)) swap(order[0], order[1]);
                if ((rng() & 2)) swap(order[1], order[2]);
                for (int k = 0; k < 3; ++k) {
                    int lit = cl[order[k]];
                    int v = abs(lit) - 1;
                    int br = breakCount(v);
                    if (br < bestBr) {
                        bestBr = br;
                        bestVar = v;
                        if (bestBr == 0) break;
                    }
                }
                chosenVar = bestVar;
            }
            flipVar(chosenVar);

            int curUnsat = (int)unsat.size();
            if (curUnsat < bestUnsat) {
                bestUnsat = curUnsat;
                bestAssign = assign;
                if (bestUnsat == 0) {
                    for (int i = 0; i < n; ++i) {
                        cout << (int)bestAssign[i] << (i + 1 == n ? '\n' : ' ');
                    }
                    return 0;
                }
            }

            if ((step & 1023) == 0) {
                if (time_elapsed() >= TIME_LIMIT) break;
            }
        }
        ++restart;
    }

    // Time up; output best found assignment
    for (int i = 0; i < n; ++i) {
        cout << (int)bestAssign[i] << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}