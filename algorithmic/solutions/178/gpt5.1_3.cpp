#include <bits/stdc++.h>
using namespace std;

static inline bool eval_clause(int idx, const vector<char>& assign, const vector<array<int,3>>& clause) {
    const auto &cl = clause[idx];
    int lit = cl[0];
    if (lit > 0) {
        if (assign[lit]) return true;
    } else {
        if (!assign[-lit]) return true;
    }
    lit = cl[1];
    if (lit > 0) {
        if (assign[lit]) return true;
    } else {
        if (!assign[-lit]) return true;
    }
    lit = cl[2];
    if (lit > 0) {
        if (assign[lit]) return true;
    } else {
        if (!assign[-lit]) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clause(m);
    vector<vector<int>> adj(n + 1);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clause[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; ++k) {
            int v = abs(lits[k]);
            if (v >= 1 && v <= n) adj[v].push_back(i);
        }
    }

    for (int v = 1; v <= n; ++v) {
        auto &vec = adj[v];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    vector<char> best_assign(n + 1, 0);

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);
    uniform_int_distribution<int> bitdist(0, 1);

    int best_s = -1;
    vector<char> assign(n + 1);
    vector<char> clauseSat(m);

    const int MAX_RESTARTS = 30;
    const int MAX_STEPS = 300;

    for (int r = 0; r < MAX_RESTARTS; ++r) {
        for (int i = 1; i <= n; ++i) {
            assign[i] = (char)bitdist(rng);
        }

        int cur_s = 0;
        for (int ci = 0; ci < m; ++ci) {
            bool sat = eval_clause(ci, assign, clause);
            clauseSat[ci] = sat;
            if (sat) ++cur_s;
        }

        if (cur_s > best_s) {
            best_s = cur_s;
            best_assign = assign;
            if (best_s == m) break;
        }

        for (int step = 0; step < MAX_STEPS; ++step) {
            int best_var = -1;
            int best_delta = 0;

            for (int v = 1; v <= n; ++v) {
                if (adj[v].empty()) continue;

                assign[v] ^= 1;

                int delta = 0;
                for (int ci : adj[v]) {
                    bool old_sat = clauseSat[ci];
                    bool new_sat = eval_clause(ci, assign, clause);
                    if (new_sat != old_sat) delta += new_sat ? 1 : -1;
                }

                assign[v] ^= 1;

                if (delta > best_delta) {
                    best_delta = delta;
                    best_var = v;
                }
            }

            if (best_delta <= 0 || best_var == -1) break;

            assign[best_var] ^= 1;
            for (int ci : adj[best_var]) {
                bool old_sat = clauseSat[ci];
                bool new_sat = eval_clause(ci, assign, clause);
                if (new_sat != old_sat) {
                    clauseSat[ci] = new_sat;
                    cur_s += new_sat ? 1 : -1;
                }
            }

            if (cur_s > best_s) {
                best_s = cur_s;
                best_assign = assign;
                if (best_s == m) break;
            }
        }

        if (best_s == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (best_assign[i] ? 1 : 0);
    }
    cout << '\n';

    return 0;
}