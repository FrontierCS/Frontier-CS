#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

struct Clause {
    int l[3];
};

bool evalClause(const Clause &cl, const vector<int> &val) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl.l[k];
        int var = lit > 0 ? lit : -lit;
        int x = val[var];
        if (lit > 0) {
            if (x) return true;
        } else {
            if (!x) return true;
        }
    }
    return false;
}

bool evalClauseFlipVar(const Clause &cl, const vector<int> &val, int v) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl.l[k];
        int var = lit > 0 ? lit : -lit;
        int x = val[var];
        if (var == v) x ^= 1;
        if (lit > 0) {
            if (x) return true;
        } else {
            if (!x) return true;
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

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i].l[0] = a;
        clauses[i].l[1] = b;
        clauses[i].l[2] = c;
        int arr[3] = {a, b, c};
        for (int k = 0; k < 3; ++k) {
            int lit = arr[k];
            int var = lit > 0 ? lit : -lit;
            if (var >= 1 && var <= n) {
                occ[var].push_back(i);
            }
        }
    }

    // Deduplicate clause indices per variable to avoid double counting
    for (int v = 1; v <= n; ++v) {
        auto &vec = occ[v];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    vector<int> val(n + 1, 0);
    if (n > 0) {
        mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
        for (int i = 1; i <= n; ++i) {
            val[i] = rng() & 1;
        }
    }

    vector<char> clauseSat(m, 0);
    int totSat = 0;
    for (int i = 0; i < m; ++i) {
        bool sat = evalClause(clauses[i], val);
        clauseSat[i] = sat;
        if (sat) ++totSat;
    }

    int maxIters = 1000;
    for (int it = 0; it < maxIters; ++it) {
        int bestDelta = 0;
        int bestVar = -1;

        for (int v = 1; v <= n; ++v) {
            int delta = 0;
            const auto &vec = occ[v];
            int sz = (int)vec.size();
            for (int j = 0; j < sz; ++j) {
                int ci = vec[j];
                bool oldSat = clauseSat[ci];
                bool newSat = evalClauseFlipVar(clauses[ci], val, v);
                delta += (int)newSat - (int)oldSat;
            }
            if (delta > bestDelta) {
                bestDelta = delta;
                bestVar = v;
            }
        }

        if (bestDelta <= 0 || bestVar == -1) break;

        int v = bestVar;
        val[v] ^= 1;
        auto &vec = occ[v];
        int sz = (int)vec.size();
        for (int j = 0; j < sz; ++j) {
            int ci = vec[j];
            bool oldSat = clauseSat[ci];
            bool newSat = evalClause(clauses[ci], val);
            clauseSat[ci] = newSat;
            totSat += (int)newSat - (int)oldSat;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << val[i];
    }
    cout << '\n';

    return 0;
}