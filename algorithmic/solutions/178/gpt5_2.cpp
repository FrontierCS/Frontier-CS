#include <bits/stdc++.h>
using namespace std;

struct Occ { int clause; int sign; }; // sign: +1 for positive, -1 for negative

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clauses(m);
    vector<vector<Occ>> occ(n + 1);
    vector<pair<int,int>> posNeg(n + 1, {0, 0}); // {posCount, negCount}

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int var = abs(lit);
            int sign = (lit > 0) ? +1 : -1;
            occ[var].push_back({i, sign});
            if (sign > 0) posNeg[var].first++;
            else posNeg[var].second++;
        }
    }

    // Handle trivial case
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    std::random_device rd;
    std::mt19937 rng(rd());
    std::uniform_real_distribution<double> real01(0.0, 1.0);

    auto now_ms = []() -> long long {
        return chrono::duration_cast<chrono::milliseconds>(
            chrono::steady_clock::now().time_since_epoch()
        ).count();
    };

    const long long timeLimitMs = 900; // time budget in ms
    const long long startTime = now_ms();

    vector<int> bestAssign(n + 1, 0);
    int bestS = -1;

    // Local search with restarts under time budget
    while (now_ms() - startTime < timeLimitMs) {
        // Initial assignment: majority heuristic with randomness on ties
        vector<int> assign(n + 1, 0);
        for (int v = 1; v <= n; ++v) {
            if (posNeg[v].first > posNeg[v].second) assign[v] = 1;
            else if (posNeg[v].first < posNeg[v].second) assign[v] = 0;
            else assign[v] = (rng() & 1);
        }

        // Compute initial sat counts and unsatisfied set
        vector<int> satcnt(m, 0);
        int satisfied = 0;
        vector<int> unsat;
        unsat.reserve(m);
        vector<int> posInUnsat(m, -1);

        auto add_unsat = [&](int cl) {
            if (posInUnsat[cl] != -1) return;
            posInUnsat[cl] = (int)unsat.size();
            unsat.push_back(cl);
        };
        auto remove_unsat = [&](int cl) {
            int pos = posInUnsat[cl];
            if (pos == -1) return;
            int last = unsat.back();
            unsat[pos] = last;
            posInUnsat[last] = pos;
            unsat.pop_back();
            posInUnsat[cl] = -1;
        };

        for (int i = 0; i < m; ++i) {
            int sc = 0;
            int lits[3] = {clauses[i][0], clauses[i][1], clauses[i][2]};
            for (int j = 0; j < 3; ++j) {
                int lit = lits[j];
                int var = abs(lit);
                bool litSat = (lit > 0) ? (assign[var] == 1) : (assign[var] == 0);
                if (litSat) sc++;
            }
            satcnt[i] = sc;
            if (sc > 0) satisfied++;
            else add_unsat(i);
        }

        if (satisfied > bestS) {
            bestS = satisfied;
            bestAssign = assign;
            if (bestS == m) break;
        }

        auto computeDelta = [&](int v) -> int {
            int val = assign[v];
            int delta = 0;
            for (const auto& oc : occ[v]) {
                int cl = oc.clause;
                int sc = satcnt[cl];
                bool litSatBefore = (oc.sign > 0) ? (val == 1) : (val == 0);
                if (sc == 0) {
                    // Clause currently unsatisfied; flipping v makes this literal true
                    if (!litSatBefore) delta += 1;
                } else if (sc == 1) {
                    // Clause has exactly one true literal
                    if (litSatBefore) delta -= 1;
                }
                // sc >= 2: no effect on satisfied count
            }
            return delta;
        };

        auto flipVar = [&](int v) {
            int val = assign[v];
            int newVal = 1 - val;
            assign[v] = newVal;
            for (const auto& oc : occ[v]) {
                int cl = oc.clause;
                int sc = satcnt[cl];
                bool litSatBefore = (oc.sign > 0) ? (val == 1) : (val == 0);
                bool litSatAfter  = !litSatBefore;
                if (sc == 0) {
                    // From 0 to 1
                    satcnt[cl] = 1;
                    satisfied++;
                    remove_unsat(cl);
                } else if (sc == 1) {
                    if (litSatBefore) {
                        // From 1 to 0
                        satcnt[cl] = 0;
                        satisfied--;
                        add_unsat(cl);
                    } else {
                        // From 1 to 2
                        satcnt[cl] = 2;
                    }
                } else {
                    // sc >= 2
                    if (litSatBefore) {
                        satcnt[cl] = sc - 1;
                    } else {
                        satcnt[cl] = sc + 1;
                    }
                }
            }
        };

        const int MAX_STEPS = 300000;
        const double noise = 0.36;
        int steps = 0;
        int stepsSinceImprovement = 0;
        const int stagnationLimit = 5000;
        const int checkInterval = 1024;

        while (steps < MAX_STEPS) {
            if (satisfied == m) {
                if (satisfied > bestS) {
                    bestS = satisfied;
                    bestAssign = assign;
                }
                break;
            }
            if ((steps & (checkInterval - 1)) == 0) {
                if (now_ms() - startTime >= timeLimitMs) break;
            }

            steps++;
            stepsSinceImprovement++;

            if (unsat.empty()) {
                if (satisfied > bestS) {
                    bestS = satisfied;
                    bestAssign = assign;
                }
                break;
            }

            int cl = unsat[rng() % unsat.size()];
            int vars[3] = {abs(clauses[cl][0]), abs(clauses[cl][1]), abs(clauses[cl][2])};

            int chosenVar;
            if (real01(rng) < noise) {
                chosenVar = vars[rng() % 3];
            } else {
                int bestDelta = INT_MIN;
                int candidates[3];
                int candCnt = 0;
                for (int j = 0; j < 3; ++j) {
                    int v = vars[j];
                    int d = computeDelta(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        candidates[0] = v;
                        candCnt = 1;
                    } else if (d == bestDelta) {
                        candidates[candCnt++] = v;
                    }
                }
                chosenVar = candidates[rng() % candCnt];
            }

            flipVar(chosenVar);

            if (satisfied > bestS) {
                bestS = satisfied;
                bestAssign = assign;
                stepsSinceImprovement = 0;
                if (bestS == m) break;
            }

            if (stepsSinceImprovement > stagnationLimit) break; // restart
        }

        if (bestS == m) break;
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << bestAssign[i];
    }
    cout << '\n';

    return 0;
}