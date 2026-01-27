#include <bits/stdc++.h>
using namespace std;

int n, m;

struct Clause {
    int a_var, b_var;
    bool a_neg, b_neg;
};

vector<Clause> clauses;
vector<vector<int>> adj;
vector<char> val;

inline bool evalClause(int idx) {
    const Clause &cl = clauses[idx];
    bool av = cl.a_neg ? !val[cl.a_var] : (bool)val[cl.a_var];
    bool bv = cl.b_neg ? !val[cl.b_var] : (bool)val[cl.b_var];
    return av || bv;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) {
        return 0;
    }

    clauses.resize(m);
    adj.assign(n + 1, {});

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int va = abs(a), vb = abs(b);
        bool na = (a < 0), nb = (b < 0);
        clauses[i].a_var = va;
        clauses[i].a_neg = na;
        clauses[i].b_var = vb;
        clauses[i].b_neg = nb;
        if (va == vb) {
            adj[va].push_back(i);
        } else {
            adj[va].push_back(i);
            adj[vb].push_back(i);
        }
    }

    val.assign(n + 1, 0);
    vector<char> clauseSat(m);
    vector<char> bestVal(n + 1, 0);
    int bestSat = -1;

    const int RESTARTS = 6;
    const int MAX_PASSES = 50;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i + 1;

    for (int r = 0; r < RESTARTS; ++r) {
        for (int i = 1; i <= n; ++i) {
            val[i] = (char)(rng() & 1);
        }

        int curSat = 0;
        for (int i = 0; i < m; ++i) {
            bool s = evalClause(i);
            clauseSat[i] = (char)s;
            if (s) ++curSat;
        }

        if (curSat > bestSat) {
            bestSat = curSat;
            bestVal = val;
            if (bestSat == m) break;
        }

        for (int pass = 0; pass < MAX_PASSES; ++pass) {
            bool improved = false;
            shuffle(order.begin(), order.end(), rng);

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                if (adj[v].empty()) continue;

                char oldVal = val[v];
                val[v] = (char)(1 - oldVal);  // temporary flip

                int delta = 0;
                for (int c : adj[v]) {
                    bool before = clauseSat[c];
                    bool after = evalClause(c);
                    delta += (int)after - (int)before;
                }

                val[v] = oldVal;  // revert

                if (delta > 0) {
                    val[v] = (char)(1 - oldVal);  // commit flip
                    curSat += delta;
                    improved = true;
                    for (int c : adj[v]) {
                        clauseSat[c] = (char)evalClause(c);
                    }
                    if (curSat > bestSat) {
                        bestSat = curSat;
                        bestVal = val;
                        if (bestSat == m) break;
                    }
                }
            }

            if (bestSat == m || !improved) break;
        }

        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        cout << (int)bestVal[i];
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}