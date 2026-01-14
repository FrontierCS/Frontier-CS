#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int clause;
    bool pos;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    struct ClauseLit { int var; bool pos; };
    struct Clause { ClauseLit l[3]; };

    vector<Clause> clauses(m);
    vector<vector<Occ>> occ(n);
    vector<int> posCnt(n, 0), negCnt(n, 0);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        int arr[3] = {a, b, c};
        for (int k = 0; k < 3; k++) {
            int lit = arr[k];
            int v = abs(lit) - 1;
            bool pos = (lit > 0);
            clauses[i].l[k] = {v, pos};
            occ[v].push_back({i, pos});
            if (pos) posCnt[v]++; else negCnt[v]++;
        }
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto rnd01 = [&]() -> bool { return (rng() & 1u) != 0; };
    auto rndInt = [&](int lim) -> int { return (int)(rng() % (uint32_t)lim); };

    vector<uint8_t> val(n, 0), bestVal(n, 0);
    vector<uint8_t> trueCnt(m, 0);
    vector<int> posUnsat(m, -1);
    vector<int> unsat;
    int satisfied = 0, bestSatisfied = -1;

    auto clauseLitTruth = [&](const ClauseLit &lit, const vector<uint8_t> &v) -> bool {
        bool x = v[lit.var] != 0;
        return lit.pos ? x : !x;
    };

    auto removeUnsat = [&](int ci) {
        int p = posUnsat[ci];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posUnsat[last] = p;
        unsat.pop_back();
        posUnsat[ci] = -1;
    };
    auto addUnsat = [&](int ci) {
        if (posUnsat[ci] != -1) return;
        posUnsat[ci] = (int)unsat.size();
        unsat.push_back(ci);
    };

    auto initAssignment = [&](bool heuristic) {
        for (int i = 0; i < n; i++) {
            if (heuristic) {
                if (posCnt[i] > negCnt[i]) val[i] = 1;
                else if (posCnt[i] < negCnt[i]) val[i] = 0;
                else val[i] = rnd01() ? 1 : 0;
                // Add a little randomness
                if ((rng() % 100u) < 5u) val[i] ^= 1u;
            } else {
                val[i] = rnd01() ? 1 : 0;
            }
        }

        satisfied = 0;
        unsat.clear();
        fill(posUnsat.begin(), posUnsat.end(), -1);

        for (int ci = 0; ci < m; ci++) {
            int cnt = 0;
            cnt += clauseLitTruth(clauses[ci].l[0], val);
            cnt += clauseLitTruth(clauses[ci].l[1], val);
            cnt += clauseLitTruth(clauses[ci].l[2], val);
            trueCnt[ci] = (uint8_t)cnt;
            if (cnt > 0) satisfied++;
            else addUnsat(ci);
        }

        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestVal = val;
        }
    };

    auto flipVar = [&](int v) {
        uint8_t oldVal = val[v];
        uint8_t newVal = oldVal ^ 1u;
        val[v] = newVal;

        for (const auto &o : occ[v]) {
            int ci = o.clause;
            bool tBefore = o.pos ? (oldVal != 0) : (oldVal == 0);
            if (tBefore) {
                uint8_t before = trueCnt[ci];
                trueCnt[ci] = (uint8_t)(before - 1);
                if (before == 1) {
                    // became unsatisfied
                    satisfied--;
                    addUnsat(ci);
                }
            } else {
                uint8_t before = trueCnt[ci];
                trueCnt[ci] = (uint8_t)(before + 1);
                if (before == 0) {
                    // became satisfied
                    satisfied++;
                    removeUnsat(ci);
                }
            }
        }
    };

    auto deltaFlip = [&](int v) -> int {
        int delta = 0;
        uint8_t vv = val[v];
        for (const auto &o : occ[v]) {
            int ci = o.clause;
            bool tBefore = o.pos ? (vv != 0) : (vv == 0);
            if (tBefore) {
                if (trueCnt[ci] == 1) delta -= 1;
            } else {
                if (trueCnt[ci] == 0) delta += 1;
            }
        }
        return delta;
    };

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.85;
    auto timeExceeded = [&]() -> bool {
        auto now = chrono::steady_clock::now();
        double sec = chrono::duration<double>(now - start).count();
        return sec >= TIME_LIMIT_SEC;
    };

    initAssignment(true);

    int stepsSinceImprove = 0;
    int lastBest = bestSatisfied;

    // Main loop: restarts based on lack of improvement and time
    bool useHeur = false;
    while (!timeExceeded()) {
        if (unsat.empty()) break;

        // Do batches of steps, check time periodically
        for (int it = 0; it < 4096; it++) {
            if (unsat.empty()) break;

            int ci = unsat[rndInt((int)unsat.size())];

            int vars[3] = { clauses[ci].l[0].var, clauses[ci].l[1].var, clauses[ci].l[2].var };

            int chosenV = vars[0];

            // Noise: sometimes random choice
            if ((rng() % 100u) < 30u) {
                chosenV = vars[rndInt(3)];
            } else {
                int bestD = INT_MIN;
                int cand[3], cc = 0;
                for (int k = 0; k < 3; k++) {
                    int v = vars[k];
                    int d = deltaFlip(v);
                    if (d > bestD) {
                        bestD = d;
                        cc = 0;
                        cand[cc++] = v;
                    } else if (d == bestD) {
                        cand[cc++] = v;
                    }
                }
                chosenV = cand[rndInt(cc)];
            }

            flipVar(chosenV);

            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestVal = val;
                stepsSinceImprove = 0;
                lastBest = bestSatisfied;
                if (bestSatisfied == m) break;
            } else {
                stepsSinceImprove++;
            }

            if (stepsSinceImprove > 20000) break;
        }

        if (bestSatisfied == m) break;
        if (timeExceeded()) break;

        if (stepsSinceImprove > 20000) {
            // restart
            useHeur = !useHeur;
            initAssignment(useHeur);
            stepsSinceImprove = 0;
        } else if (bestSatisfied == lastBest && (rng() % 100u) < 5u) {
            // occasional random restart
            initAssignment(false);
            stepsSinceImprove = 0;
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << "\n";
    return 0;
}