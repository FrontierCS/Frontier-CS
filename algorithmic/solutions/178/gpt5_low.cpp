#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b, c;
};

static inline bool litValue(int lit, const vector<uint8_t>& assign) {
    int v = abs(lit);
    bool val = assign[v];
    return lit > 0 ? val : !val;
}

static inline bool clauseValue(const Clause& cl, const vector<uint8_t>& assign) {
    return litValue(cl.a, assign) || litValue(cl.b, assign) || litValue(cl.c, assign);
}

static inline bool clauseValueUnderFlip(const Clause& cl, const vector<uint8_t>& assign, int var) {
    // Evaluate clause assuming variable 'var' is flipped
    auto evalLit = [&](int lit)->bool{
        int v = abs(lit);
        bool val = assign[v];
        if (v == var) val = !val;
        return lit > 0 ? val : !val;
    };
    return evalLit(cl.a) || evalLit(cl.b) || evalLit(cl.c);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].a >> clauses[i].b >> clauses[i].c;
    }

    // Occurrence lists: for each variable, list of clause indices where it appears
    vector<vector<int>> occ(n + 1);
    for (int i = 0; i < m; ++i) {
        int la = abs(clauses[i].a);
        int lb = abs(clauses[i].b);
        int lc = abs(clauses[i].c);
        occ[la].push_back(i);
        occ[lb].push_back(i);
        occ[lc].push_back(i);
    }

    // Trivial case
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Random engine
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Track best assignment
    vector<uint8_t> bestAssign(n + 1, 0);
    int bestS = -1;

    // Timing
    const double TIME_LIMIT_SEC = 0.95;
    auto t0 = chrono::high_resolution_clock::now();

    // Structures for a run
    vector<uint8_t> assign(n + 1, 0);
    vector<uint8_t> satFlag(m, 0);
    vector<int> unsat; unsat.reserve(m);
    vector<int> pos(m, -1);

    auto rebuild_unsat = [&](int& s) {
        s = 0;
        unsat.clear();
        std::fill(pos.begin(), pos.end(), -1);
        for (int i = 0; i < m; ++i) {
            bool sat = clauseValue(clauses[i], assign);
            satFlag[i] = sat;
            if (!sat) {
                pos[i] = (int)unsat.size();
                unsat.push_back(i);
            } else {
                s++;
            }
        }
    };

    auto setClauseSat = [&](int idx, bool newSat, int& s) {
        bool oldSat = satFlag[idx];
        if (oldSat == newSat) return;
        satFlag[idx] = newSat;
        if (newSat) {
            // remove from unsat
            int p = pos[idx];
            if (p != -1) {
                int last = unsat.back();
                unsat[p] = last;
                pos[last] = p;
                unsat.pop_back();
                pos[idx] = -1;
            }
            s++;
        } else {
            // add to unsat
            if (pos[idx] == -1) {
                pos[idx] = (int)unsat.size();
                unsat.push_back(idx);
            }
            s--;
        }
    };

    auto delta_var = [&](int var)->int {
        int delta = 0;
        for (int ci : occ[var]) {
            bool before = satFlag[ci];
            bool after = clauseValueUnderFlip(clauses[ci], assign, var);
            if (!before && after) delta += 1;
            else if (before && !after) delta -= 1;
        }
        return delta;
    };

    auto flip_var = [&](int var, int& s) {
        assign[var] ^= 1;
        for (int ci : occ[var]) {
            bool after = clauseValue(clauses[ci], assign);
            setClauseSat(ci, after, s);
        }
    };

    uniform_real_distribution<double> prob01(0.0, 1.0);
    uniform_int_distribution<int> coin01(0, 1);

    // WalkSAT parameters
    const double noise = 0.5;
    const int MAX_STEPS_PER_RESTART = 20000;

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        // Random initialization
        for (int i = 1; i <= n; ++i) assign[i] = (uint8_t)(rng() & 1ull);

        int s = 0;
        rebuild_unsat(s);

        if (s > bestS) {
            bestS = s;
            bestAssign = assign;
            if (bestS == m) break;
        }

        for (int step = 0; step < MAX_STEPS_PER_RESTART; ++step) {
            // Check time
            now = chrono::high_resolution_clock::now();
            elapsed = chrono::duration<double>(now - t0).count();
            if (elapsed > TIME_LIMIT_SEC) break;

            if (unsat.empty()) {
                // All satisfied
                if (s > bestS) {
                    bestS = s;
                    bestAssign = assign;
                }
                break;
            }

            // Pick an unsatisfied clause
            int ci = unsat[rng() % unsat.size()];
            const Clause& cl = clauses[ci];

            int vars[3] = {abs(cl.a), abs(cl.b), abs(cl.c)};
            int pickVar;

            if (prob01(rng) < noise) {
                // Random variable from the clause
                pickVar = vars[rng() % 3];
            } else {
                // Best variable by max delta
                int bestDelta = INT_MIN;
                int bestCount = 0;
                int candidates[3];
                for (int k = 0; k < 3; ++k) {
                    int v = vars[k];
                    int d = delta_var(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        candidates[0] = v;
                        bestCount = 1;
                    } else if (d == bestDelta) {
                        candidates[bestCount++] = v;
                    }
                }
                pickVar = candidates[rng() % bestCount];
            }

            flip_var(pickVar, s);

            if (s > bestS) {
                bestS = s;
                bestAssign = assign;
                if (bestS == m) break;
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}