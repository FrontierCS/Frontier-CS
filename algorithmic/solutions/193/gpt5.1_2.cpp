#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].a >> clauses[i].b;
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Build occurrence lists: each clause index appears at most once per variable
    vector<vector<int>> appear(n + 1);
    for (int i = 0; i < m; ++i) {
        int a = clauses[i].a, b = clauses[i].b;
        int va = abs(a), vb = abs(b);
        if (va == vb) {
            appear[va].push_back(i);
        } else {
            appear[va].push_back(i);
            appear[vb].push_back(i);
        }
    }

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    const long long MAX_OPS = 20000000LL;
    const int MAX_RESTARTS = 30;
    const int RANDOM_MOVE_PERCENT = 30; // percentage of random moves vs greedy within unsat clause

    vector<char> bestAssignment(n + 1, 0);
    int bestSat = -1;

    vector<char> ass(n + 1), clauseSat(m);
    vector<int> make(n + 1), brk(n + 1);
    vector<int> unsat;
    unsat.reserve(m);
    vector<int> whereInUnsat(m);

    long long ops = 0;

    auto updateContribForClause = [&](int ci, const vector<char> &assign, int sign) {
        const Clause &C = clauses[ci];
        int a = C.a, b = C.b;
        int va = abs(a), vb = abs(b);
        bool val1 = (a > 0 ? assign[va] : !assign[va]);
        bool val2 = (b > 0 ? assign[vb] : !assign[vb]);
        bool sat_before = (val1 || val2);

        // For variable va
        bool val1_va = !val1;      // literal a toggled
        bool val2_va = val2;
        if (vb == va) val2_va = !val2_va; // if same variable, literal b also toggled
        bool sat_after_va = (val1_va || val2_va);
        if (sat_before && !sat_after_va) brk[va] += sign;
        else if (!sat_before && sat_after_va) make[va] += sign;

        // For variable vb if distinct
        if (vb != va) {
            bool val1_vb = val1;
            bool val2_vb = !val2;  // literal b toggled
            bool sat_after_vb = (val1_vb || val2_vb);
            if (sat_before && !sat_after_vb) brk[vb] += sign;
            else if (!sat_before && sat_after_vb) make[vb] += sign;
        }
    };

    for (int restart = 0; restart < MAX_RESTARTS && ops < MAX_OPS && bestSat < m; ++restart) {
        // Random initial assignment
        for (int i = 1; i <= n; ++i) {
            ass[i] = (char)(rng() & 1);
        }

        // Initialize satisfaction and unsatisfied clause list
        unsat.clear();
        fill(whereInUnsat.begin(), whereInUnsat.end(), -1);
        int curSat = 0;
        for (int i = 0; i < m; ++i) {
            int a = clauses[i].a, b = clauses[i].b;
            int va = abs(a), vb = abs(b);
            bool val1 = (a > 0 ? ass[va] : !ass[va]);
            bool val2 = (b > 0 ? ass[vb] : !ass[vb]);
            bool sat = (val1 || val2);
            clauseSat[i] = (char)sat;
            if (sat) ++curSat;
            else {
                whereInUnsat[i] = (int)unsat.size();
                unsat.push_back(i);
            }
        }

        // Initialize break/make counts
        fill(make.begin(), make.end(), 0);
        fill(brk.begin(), brk.end(), 0);
        for (int i = 0; i < m; ++i) {
            updateContribForClause(i, ass, +1);
            ++ops;
        }

        if (curSat > bestSat) {
            bestSat = curSat;
            bestAssignment = ass;
            if (bestSat == m) break;
        }

        int maxStepsPerRestart = 4 * m + 1000;
        int stepsWithoutImprovement = 0;

        for (int step = 0; step < maxStepsPerRestart && ops < MAX_OPS && !unsat.empty() && bestSat < m; ++step) {
            // Pick random unsatisfied clause
            int ci = unsat[(size_t)(rng() % unsat.size())];
            const Clause &C = clauses[ci];
            int a = C.a, b = C.b;
            int var1 = abs(a), var2 = abs(b);

            int chosenVar;
            if (var1 == var2) {
                chosenVar = var1;
            } else {
                bool randomMove = ((int)(rng() % 100) < RANDOM_MOVE_PERCENT);
                if (randomMove) {
                    chosenVar = (rng() & 1) ? var1 : var2;
                } else {
                    int delta1 = make[var1] - brk[var1];
                    int delta2 = make[var2] - brk[var2];
                    if (delta1 > delta2) chosenVar = var1;
                    else if (delta2 > delta1) chosenVar = var2;
                    else chosenVar = (rng() & 1) ? var1 : var2;
                }
            }

            int v = chosenVar;
            const vector<int> &clist = appear[v];

            // Remove old contributions and update clause satisfaction for clauses containing v
            for (int idx = 0; idx < (int)clist.size(); ++idx) {
                int cindex = clist[idx];
                const Clause &CC = clauses[cindex];
                int aa = CC.a, bb = CC.b;
                int va = abs(aa), vb = abs(bb);

                // Remove contributions under old assignment
                updateContribForClause(cindex, ass, -1);
                ++ops;

                bool val1_before = (aa > 0 ? ass[va] : !ass[va]);
                bool val2_before = (bb > 0 ? ass[vb] : !ass[vb]);
                bool sat_before = (val1_before || val2_before);

                bool val1_after = val1_before;
                bool val2_after = val2_before;
                if (va == v) val1_after = !val1_after;
                if (vb == v) val2_after = !val2_after;
                bool sat_after = (val1_after || val2_after);

                if (!sat_before && sat_after) {
                    ++curSat;
                    int pos = whereInUnsat[cindex];
                    if (pos != -1) {
                        int lastClause = unsat.back();
                        unsat[pos] = lastClause;
                        whereInUnsat[lastClause] = pos;
                        unsat.pop_back();
                        whereInUnsat[cindex] = -1;
                    }
                } else if (sat_before && !sat_after) {
                    --curSat;
                    if (whereInUnsat[cindex] == -1) {
                        whereInUnsat[cindex] = (int)unsat.size();
                        unsat.push_back(cindex);
                    }
                }
                clauseSat[cindex] = (char)sat_after;
            }

            // Flip variable
            ass[v] ^= 1;

            // Add new contributions under updated assignment
            for (int idx = 0; idx < (int)clist.size(); ++idx) {
                int cindex = clist[idx];
                updateContribForClause(cindex, ass, +1);
                ++ops;
            }

            if (curSat > bestSat) {
                bestSat = curSat;
                bestAssignment = ass;
                stepsWithoutImprovement = 0;
                if (bestSat == m) break;
            } else {
                ++stepsWithoutImprovement;
                if (stepsWithoutImprovement > 2 * m) {
                    break; // stagnation, restart
                }
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << (int)bestAssignment[i] << (i == n ? '\n' : ' ');
    }

    return 0;
}