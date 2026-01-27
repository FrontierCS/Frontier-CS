#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int, 3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    vector<vector<int>> appear(n + 1);
    for (int idx = 0; idx < m; ++idx) {
        for (int k = 0; k < 3; ++k) {
            int var = abs(clauses[idx][k]);
            appear[var].push_back(idx);
        }
    }
    for (int v = 1; v <= n; ++v) {
        auto &vec = appear[v];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    auto checkClause = [&](int idx, const vector<int> &assign) -> bool {
        const auto &cl = clauses[idx];
        for (int k = 0; k < 3; ++k) {
            int lit = cl[k];
            int var = abs(lit);
            int val = assign[var];
            if ((lit > 0 && val == 1) || (lit < 0 && val == 0)) return true;
        }
        return false;
    };

    auto checkClauseAfterFlip = [&](int idx, int v, const vector<int> &assign) -> bool {
        const auto &cl = clauses[idx];
        for (int k = 0; k < 3; ++k) {
            int lit = cl[k];
            int var = abs(lit);
            int val = assign[var];
            if (var == v) val ^= 1;
            if ((lit > 0 && val == 1) || (lit < 0 && val == 0)) return true;
        }
        return false;
    };

    vector<int> bestAssign(n + 1, 0);
    int bestSat = -1;

    const int RESTARTS = 30;
    const int STEPS = 500;

    vector<int> assign(n + 1);
    vector<bool> clauseSat(m);
    int satCount;

    for (int r = 0; r < RESTARTS; ++r) {
        for (int i = 1; i <= n; ++i) {
            assign[i] = rng() & 1;
        }

        satCount = 0;
        for (int idx = 0; idx < m; ++idx) {
            bool ok = false;
            const auto &cl = clauses[idx];
            for (int k = 0; k < 3; ++k) {
                int lit = cl[k];
                int var = abs(lit);
                int val = assign[var];
                if ((lit > 0 && val == 1) || (lit < 0 && val == 0)) {
                    ok = true;
                    break;
                }
            }
            clauseSat[idx] = ok;
            if (ok) ++satCount;
        }
        if (satCount > bestSat) {
            bestSat = satCount;
            bestAssign = assign;
            if (bestSat == m) break;
        }

        for (int step = 0; step < STEPS; ++step) {
            if (satCount == m) break;

            int bestDelta = INT_MIN;
            int bestVar = 1;
            for (int v = 1; v <= n; ++v) {
                int delta = 0;
                for (int idx : appear[v]) {
                    bool before = clauseSat[idx];
                    bool after = checkClauseAfterFlip(idx, v, assign);
                    if (after != before) delta += after ? 1 : -1;
                }
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestVar = v;
                }
            }

            if (bestDelta <= 0) {
                uniform_int_distribution<int> dist(1, n);
                bestVar = dist(rng);
            }

            assign[bestVar] ^= 1;
            for (int idx : appear[bestVar]) {
                bool before = clauseSat[idx];
                bool after = checkClause(idx, assign);
                if (before != after) {
                    clauseSat[idx] = after;
                    if (after) ++satCount;
                    else --satCount;
                }
            }

            if (satCount > bestSat) {
                bestSat = satCount;
                bestAssign = assign;
                if (bestSat == m) break;
            }
        }
        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << bestAssign[i];
    }
    cout << "\n";
    return 0;
}