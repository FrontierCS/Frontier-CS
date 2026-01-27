#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int var[3];
    bool neg[3];
};

static inline double now_sec(const chrono::steady_clock::time_point& st) {
    return chrono::duration<double>(chrono::steady_clock::now() - st).count();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<Clause> clauses(m);
    vector<vector<int>> occ(n);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; j++) {
            int x = lits[j];
            clauses[i].var[j] = abs(x) - 1;
            clauses[i].neg[j] = (x < 0);
            occ[clauses[i].var[j]].push_back(i);
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
    uniform_real_distribution<double> unif01(0.0, 1.0);

    vector<int> assign(n), bestAssign(n);
    vector<char> sat(m, 0);
    vector<int> pos(m, -1);
    vector<int> unsat;

    auto evalClause = [&](int cid, int flipVar) -> bool {
        const Clause &cl = clauses[cid];
        for (int k = 0; k < 3; k++) {
            int v = cl.var[k];
            int val = assign[v];
            if (v == flipVar) val ^= 1;
            bool litTrue = cl.neg[k] ? (val == 0) : (val == 1);
            if (litTrue) return true;
        }
        return false;
    };

    auto removeUnsat = [&](int cid) {
        int idx = pos[cid];
        if (idx < 0) return;
        int last = unsat.back();
        unsat[idx] = last;
        pos[last] = idx;
        unsat.pop_back();
        pos[cid] = -1;
    };

    auto addUnsat = [&](int cid) {
        if (pos[cid] >= 0) return;
        pos[cid] = (int)unsat.size();
        unsat.push_back(cid);
    };

    int satisfiedCount = 0;

    auto rebuildState = [&]() {
        unsat.clear();
        fill(pos.begin(), pos.end(), -1);
        satisfiedCount = 0;
        for (int i = 0; i < m; i++) {
            bool ok = evalClause(i, -1);
            sat[i] = ok ? 1 : 0;
            if (ok) satisfiedCount++;
            else addUnsat(i);
        }
    };

    auto flipVarApply = [&](int v) {
        assign[v] ^= 1;
        for (int cid : occ[v]) {
            bool prev = sat[cid];
            bool now = evalClause(cid, -1);
            if (prev != now) {
                sat[cid] = now ? 1 : 0;
                if (now) {
                    satisfiedCount++;
                    removeUnsat(cid);
                } else {
                    satisfiedCount--;
                    addUnsat(cid);
                }
            }
        }
    };

    auto deltaIfFlip = [&](int v) -> int {
        int d = 0;
        for (int cid : occ[v]) {
            bool prev = sat[cid];
            bool now = evalClause(cid, v);
            if (prev != now) d += now ? 1 : -1;
        }
        return d;
    };

    auto randomAssignment = [&]() {
        for (int i = 0; i < n; i++) assign[i] = (int)(rng() & 1u);
        rebuildState();
    };

    auto greedyPolish = [&](double timeLimitSec, const chrono::steady_clock::time_point& st) {
        while (now_sec(st) < timeLimitSec) {
            int bestV = -1, bestD = 0;
            for (int v = 0; v < n; v++) {
                int d = deltaIfFlip(v);
                if (d > bestD) {
                    bestD = d;
                    bestV = v;
                }
            }
            if (bestD <= 0) break;
            flipVarApply(bestV);
        }
    };

    const auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.9;
    const double NOISE = 0.45;

    int bestSat = -1;

    while (now_sec(start) < TIME_LIMIT) {
        randomAssignment();

        if (satisfiedCount > bestSat) {
            bestSat = satisfiedCount;
            bestAssign = assign;
            if (bestSat == m) break;
        }

        int steps = 0;
        int maxSteps = 50000;
        while (steps < maxSteps && now_sec(start) < TIME_LIMIT) {
            steps++;
            if (unsat.empty()) break;

            int cid = unsat[rng() % unsat.size()];
            const Clause &cl = clauses[cid];

            int vars[3] = {cl.var[0], cl.var[1], cl.var[2]};
            int chosen = vars[rng() % 3];

            int bestV = vars[0];
            int bestD = deltaIfFlip(bestV);

            for (int k = 1; k < 3; k++) {
                int v = vars[k];
                int d = deltaIfFlip(v);
                if (d > bestD || (d == bestD && (rng() & 1u))) {
                    bestD = d;
                    bestV = v;
                }
            }

            double r = unif01(rng);
            if (bestD > 0 && r > NOISE) chosen = bestV;

            flipVarApply(chosen);

            if (satisfiedCount > bestSat) {
                bestSat = satisfiedCount;
                bestAssign = assign;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    assign = bestAssign;
    rebuildState();
    greedyPolish(TIME_LIMIT, start);
    if (satisfiedCount > bestSat) {
        bestSat = satisfiedCount;
        bestAssign = assign;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << bestAssign[i];
    }
    cout << "\n";
    return 0;
}