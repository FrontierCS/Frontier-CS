#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v1, v2; // variable indices (1..n)
    bool s1, s2; // sign: true means literal is variable as is, false means negated
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<int>> varClauses(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int va = abs(a), vb = abs(b);
        bool sa = (a > 0);
        bool sb = (b > 0);
        clauses[i] = {va, vb, sa, sb};
        if (va >= 1 && va <= n) varClauses[va].push_back(i);
        if (vb >= 1 && vb <= n) varClauses[vb].push_back(i);
    }

    auto evalLiteral = [&](int var, bool sign, const vector<int>& val)->bool {
        return (val[var] == (int)sign);
    };

    auto climb = [&](vector<int>& val, vector<int>& bestVal, int& bestSat){
        int M = m;
        vector<char> sat(M, 0);
        int totalSat = 0;
        // compute sat
        for (int i = 0; i < M; ++i) {
            bool l1 = evalLiteral(clauses[i].v1, clauses[i].s1, val);
            bool l2 = evalLiteral(clauses[i].v2, clauses[i].s2, val);
            sat[i] = (l1 || l2);
            totalSat += sat[i];
        }
        // compute delta
        vector<int> delta(n + 1, 0);
        auto clauseAfterFlip = [&](int idx, int var)->int {
            const Clause& c = clauses[idx];
            bool l1 = evalLiteral(c.v1, c.s1, val);
            bool l2 = evalLiteral(c.v2, c.s2, val);
            bool before = (l1 || l2);
            bool after;
            if (c.v1 == var) {
                bool l1new = ((1 - val[var]) == (int)c.s1);
                after = (l1new || l2);
            } else {
                bool l2new = ((1 - val[var]) == (int)c.s2);
                after = (l1 || l2new);
            }
            return (int)after - (int)before;
        };
        for (int v = 1; v <= n; ++v) {
            int d = 0;
            for (int ci : varClauses[v]) {
                d += clauseAfterFlip(ci, v);
            }
            delta[v] = d;
        }

        // hill climbing
        while (true) {
            int bestVar = 0;
            int bestDelta = 0;
            for (int v = 1; v <= n; ++v) {
                if (delta[v] > bestDelta) {
                    bestDelta = delta[v];
                    bestVar = v;
                }
            }
            if (bestDelta <= 0) break;
            int x = bestVar;
            // flip x
            val[x] ^= 1;
            // update affected clauses and totalSat
            vector<int> affectedVars;
            affectedVars.push_back(x);
            for (int ci : varClauses[x]) {
                int before = sat[ci];
                // recompute clause satisfaction after flip
                const Clause& c = clauses[ci];
                bool l1 = evalLiteral(c.v1, c.s1, val);
                bool l2 = evalLiteral(c.v2, c.s2, val);
                int after = (l1 || l2);
                if (before != after) {
                    sat[ci] = after;
                    totalSat += (after - before);
                }
                int y = (c.v1 == x) ? c.v2 : c.v1;
                affectedVars.push_back(y);
            }
            // recompute delta for affected variables (deduplicate)
            sort(affectedVars.begin(), affectedVars.end());
            affectedVars.erase(unique(affectedVars.begin(), affectedVars.end()), affectedVars.end());
            for (int v : affectedVars) {
                int d = 0;
                for (int ci : varClauses[v]) {
                    // compute diff if v flips now (given current val and sat)
                    const Clause& c = clauses[ci];
                    bool l1 = evalLiteral(c.v1, c.s1, val);
                    bool l2 = evalLiteral(c.v2, c.s2, val);
                    bool before = (l1 || l2);
                    bool after;
                    if (c.v1 == v) {
                        bool l1new = ((1 - val[v]) == (int)c.s1);
                        after = (l1new || l2);
                    } else {
                        bool l2new = ((1 - val[v]) == (int)c.s2);
                        after = (l1 || l2new);
                    }
                    d += (int)after - (int)before;
                }
                delta[v] = d;
            }
        }

        if (totalSat > bestSat) {
            bestSat = totalSat;
            bestVal = val;
        }
    };

    // Randomized restarts
    int bestSat = -1;
    vector<int> bestVal(n + 1, 0);
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    int restarts = 10;
    for (int r = 0; r < restarts; ++r) {
        vector<int> val(n + 1, 0);
        for (int i = 1; i <= n; ++i) val[i] = (rng() & 1);
        climb(val, bestVal, bestSat);
    }
    if (bestSat < 0) {
        // no clauses, or failed: just output zeros
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << bestVal[i];
    }
    cout << '\n';
    return 0;
}