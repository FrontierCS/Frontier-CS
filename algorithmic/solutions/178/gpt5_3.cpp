#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];       // variable indices (1..n)
    bool isPos[3];  // true if literal is positive
    bool litSat[3]; // current satisfaction of each literal
    int satCount;   // number of satisfied literals
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int t = 0; t < 3; ++t) {
            int x = lits[t];
            clauses[i].v[t] = abs(x);
            clauses[i].isPos[t] = (x > 0);
            clauses[i].litSat[t] = false;
        }
        clauses[i].satCount = 0;
    }

    // Edge case: no clauses
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // For each variable, store distinct clauses containing it
    vector<vector<int>> clausesForVar(n + 1);
    for (int j = 0; j < m; ++j) {
        bool seen[51] = {false};
        for (int t = 0; t < 3; ++t) {
            int v = clauses[j].v[t];
            if (!seen[v]) {
                clausesForVar[v].push_back(j);
                seen[v] = true;
            }
        }
    }

    // Random generator
    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Unsatisfied set helper
    vector<int> unsat;             // list of unsatisfied clause indices
    vector<int> posInUnsat(m, -1); // position in unsat list or -1 if not unsatisfied

    auto addUnsat = [&](int j) {
        if (posInUnsat[j] == -1) {
            posInUnsat[j] = (int)unsat.size();
            unsat.push_back(j);
        }
    };
    auto removeUnsat = [&](int j) {
        int pos = posInUnsat[j];
        if (pos != -1) {
            int last = unsat.back();
            swap(unsat[pos], unsat.back());
            posInUnsat[last] = pos;
            posInUnsat[j] = -1;
            unsat.pop_back();
        }
    };

    // Assignment representation: 0/1
    vector<char> assign(n + 1, 0);

    auto initRandomAssignment = [&](vector<char>& asg) {
        for (int i = 1; i <= n; ++i) asg[i] = (rng() & 1) ? 1 : 0;
        // compute clause satisfaction
        for (int j = 0; j < m; ++j) {
            int cnt = 0;
            for (int t = 0; t < 3; ++t) {
                int v = clauses[j].v[t];
                bool val = asg[v];
                bool sat = clauses[j].isPos[t] ? val : !val;
                clauses[j].litSat[t] = sat;
                if (sat) ++cnt;
            }
            clauses[j].satCount = cnt;
        }
        // build unsatisfied set
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int j = 0; j < m; ++j) {
            if (clauses[j].satCount == 0) addUnsat(j);
        }
    };

    auto flipVar = [&](int v, vector<char>& asg) {
        asg[v] ^= 1;
        for (int j : clausesForVar[v]) {
            Clause &c = clauses[j];
            int oldSatCount = c.satCount;
            // toggle all occurrences of v in clause j
            for (int t = 0; t < 3; ++t) {
                if (c.v[t] == v) {
                    c.litSat[t] = !c.litSat[t];
                    if (c.litSat[t]) ++c.satCount; else --c.satCount;
                }
            }
            if (oldSatCount == 0 && c.satCount > 0) {
                removeUnsat(j);
            } else if (oldSatCount > 0 && c.satCount == 0) {
                addUnsat(j);
            }
        }
    };

    auto deltaIfFlip = [&](int v, const vector<char>& asg) -> int {
        (void)asg; // as we use clauses' litSat/satCount directly
        int delta = 0;
        for (int j : clausesForVar[v]) {
            Clause const &c = clauses[j];
            int oldSat = (c.satCount > 0) ? 1 : 0;
            int occ = 0;
            int kBefore = 0;
            if (c.v[0] == v) { ++occ; if (c.litSat[0]) ++kBefore; }
            if (c.v[1] == v) { ++occ; if (c.litSat[1]) ++kBefore; }
            if (c.v[2] == v) { ++occ; if (c.litSat[2]) ++kBefore; }
            int newSatCount = c.satCount + occ - 2 * kBefore;
            int newSat = (newSatCount > 0) ? 1 : 0;
            delta += (newSat - oldSat);
        }
        return delta;
    };

    // Parameters
    const int CHECK_INTERVAL = 1024;
    const int64_t TIME_LIMIT_MS = 900; // try to stay under typical 1s limit
    const int MAX_STEPS_PER_RESTART = 1000000; // fallback limit
    const int NOISE_THOUSAND = 350; // WalkSAT noise parameter p ~ 0.35

    auto start = chrono::steady_clock::now();

    vector<char> bestAssign(n + 1, 0);
    int bestSat = -1;

    int restarts = 0;
    while (true) {
        // Check time before each restart
        auto now = chrono::steady_clock::now();
        int64_t elapsed = chrono::duration_cast<chrono::milliseconds>(now - start).count();
        if (elapsed > TIME_LIMIT_MS) break;

        initRandomAssignment(assign);
        int currentSat = m - (int)unsat.size();
        if (currentSat > bestSat) {
            bestSat = currentSat;
            bestAssign = assign;
            if (bestSat == m) break;
        }

        int steps = 0;
        while (!unsat.empty()) {
            // time check occasionally
            if ((steps & (CHECK_INTERVAL - 1)) == 0) {
                now = chrono::steady_clock::now();
                elapsed = chrono::duration_cast<chrono::milliseconds>(now - start).count();
                if (elapsed > TIME_LIMIT_MS) break;
            }
            if (steps++ > MAX_STEPS_PER_RESTART) break;

            // pick random unsatisfied clause
            int cj = unsat[rng() % unsat.size()];
            // collect unique variables in this clause
            int candVarArr[3] = {clauses[cj].v[0], clauses[cj].v[1], clauses[cj].v[2]};
            // dedup
            int uniqVars[3]; int ucnt = 0;
            for (int t = 0; t < 3; ++t) {
                int v = candVarArr[t];
                bool seen = false;
                for (int k = 0; k < ucnt; ++k) if (uniqVars[k] == v) { seen = true; break; }
                if (!seen) uniqVars[ucnt++] = v;
            }

            int chosenVar;
            if ((int)(rng() % 1000) < NOISE_THOUSAND) {
                // random choice among candidates
                chosenVar = uniqVars[rng() % ucnt];
            } else {
                // greedy: pick with maximum delta
                int bestDelta = INT_MIN;
                int bestIdx = 0;
                for (int k = 0; k < ucnt; ++k) {
                    int v = uniqVars[k];
                    int d = deltaIfFlip(v, assign);
                    if (d > bestDelta) {
                        bestDelta = d;
                        bestIdx = k;
                    } else if (d == bestDelta && (rng() & 1)) {
                        bestIdx = k;
                    }
                }
                chosenVar = uniqVars[bestIdx];
            }

            flipVar(chosenVar, assign);
            currentSat = m - (int)unsat.size();
            if (currentSat > bestSat) {
                bestSat = currentSat;
                bestAssign = assign;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
        ++restarts;
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << (int)bestAssign[i] << (i == n ? '\n' : ' ');
    }

    return 0;
}