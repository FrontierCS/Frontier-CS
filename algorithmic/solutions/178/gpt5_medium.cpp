#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int lit[3];
};

static inline bool evalClause(const Clause& c, const vector<char>& A) {
    for (int k = 0; k < 3; ++k) {
        int x = c.lit[k];
        int v = abs(x);
        bool sign = x > 0;
        if (sign ? (A[v] == 1) : (A[v] == 0)) return true;
    }
    return false;
}

static inline bool evalClauseWithFlip(const Clause& c, const vector<char>& A, int flipVar) {
    for (int k = 0; k < 3; ++k) {
        int x = c.lit[k];
        int v = abs(x);
        bool sign = x > 0;
        if (v == flipVar) {
            bool val = A[v] ^ 1;
            if (sign ? (val == 1) : (val == 0)) return true;
        } else {
            if (sign ? (A[v] == 1) : (A[v] == 0)) return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<Clause> clauses(m);
    vector<vector<int>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        clauses[i].lit[2] = c;
        for (int k = 0; k < 3; ++k) {
            int x = clauses[i].lit[k];
            int v = abs(x);
            occ[v].push_back(i);
            if (x > 0) posCnt[v]++; else negCnt[v]++;
        }
    }

    // Edge case: no clauses -> any assignment is optimal
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    // RNG setup
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    std::mt19937_64 rng(seed);
    auto rand01 = [&]() -> double {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng);
    };
    auto randInt = [&](int l, int r) -> int {
        return std::uniform_int_distribution<int>(l, r)(rng);
    };

    const double TIME_LIMIT = 0.95; // seconds
    auto t_start = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    vector<char> bestA(n + 1, 0);
    int bestSat = -1;

    // Working structures
    vector<char> A(n + 1, 0);
    vector<char> sat(m, 0);
    vector<int> unsat_list; unsat_list.reserve(m);
    vector<int> pos_in_unsat(m, -1);
    auto add_unsat = [&](int idx) {
        if (pos_in_unsat[idx] == -1) {
            pos_in_unsat[idx] = (int)unsat_list.size();
            unsat_list.push_back(idx);
        }
    };
    auto remove_unsat = [&](int idx) {
        int pos = pos_in_unsat[idx];
        if (pos == -1) return;
        int last = unsat_list.back();
        unsat_list[pos] = last;
        pos_in_unsat[last] = pos;
        unsat_list.pop_back();
        pos_in_unsat[idx] = -1;
    };

    auto initialize_assignment = [&](bool heuristic_init) {
        if (heuristic_init) {
            for (int v = 1; v <= n; ++v) {
                if (posCnt[v] > negCnt[v]) A[v] = 1;
                else if (posCnt[v] < negCnt[v]) A[v] = 0;
                else A[v] = randInt(0, 1);
                if (rand01() < 0.1) A[v] ^= 1; // small noise
            }
        } else {
            for (int v = 1; v <= n; ++v) A[v] = randInt(0, 1);
        }
    };

    auto evaluate_state = [&]() -> int {
        int satCount = 0;
        unsat_list.clear();
        fill(pos_in_unsat.begin(), pos_in_unsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            sat[i] = evalClause(clauses[i], A);
            if (sat[i]) satCount++;
            else add_unsat(i);
        }
        return satCount;
    };

    auto flip_var = [&](int v, int& satCount) {
        A[v] ^= 1;
        for (int idx : occ[v]) {
            bool newSat = evalClause(clauses[idx], A);
            if (newSat != sat[idx]) {
                if (newSat) {
                    sat[idx] = 1;
                    satCount++;
                    remove_unsat(idx);
                } else {
                    sat[idx] = 0;
                    satCount--;
                    add_unsat(idx);
                }
            }
        }
    };

    const double walkProb = 0.3;
    const int plateauLimit = 4000;

    while (elapsed() < TIME_LIMIT) {
        bool heuristic_init = (rand01() < 0.6);
        initialize_assignment(heuristic_init);
        int satCount = evaluate_state();

        if (satCount > bestSat) {
            bestSat = satCount;
            bestA = A;
            if (bestSat == m) break;
        }

        int iter = 0;
        int lastImproveIter = 0;

        while (elapsed() < TIME_LIMIT) {
            if (satCount == m) {
                bestSat = satCount;
                bestA = A;
                break;
            }
            if (iter - lastImproveIter > plateauLimit) break;
            if (unsat_list.empty()) break;

            int cidx = unsat_list[randInt(0, (int)unsat_list.size() - 1)];
            const Clause& c = clauses[cidx];

            int chosenVar;
            if (rand01() < walkProb) {
                int k = randInt(0, 2);
                chosenVar = abs(c.lit[k]);
            } else {
                int bestDelta = INT_MIN;
                int candidates[3];
                int candCnt = 0;
                for (int k = 0; k < 3; ++k) {
                    int v = abs(c.lit[k]);
                    int delta = 0;
                    for (int idx : occ[v]) {
                        bool oldSat = sat[idx];
                        bool newSat = evalClauseWithFlip(clauses[idx], A, v);
                        delta += (int)newSat - (int)oldSat;
                    }
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        candidates[0] = v;
                        candCnt = 1;
                    } else if (delta == bestDelta) {
                        candidates[candCnt++] = v;
                    }
                }
                chosenVar = candidates[randInt(0, candCnt - 1)];
            }

            flip_var(chosenVar, satCount);
            iter++;

            if (satCount > bestSat) {
                bestSat = satCount;
                bestA = A;
                lastImproveIter = iter;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestA[i];
    }
    cout << '\n';
    return 0;
}