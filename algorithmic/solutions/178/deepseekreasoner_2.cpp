#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<tuple<int, int, int>> clauses(m);
    vector<vector<int>> pos_clauses(n + 1), neg_clauses(n + 1);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        auto add = [&](int lit) {
            if (lit > 0) pos_clauses[lit].push_back(i);
            else neg_clauses[-lit].push_back(i);
        };
        add(a);
        add(b);
        add(c);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) cout << "0 ";
        cout << "\n";
        return 0;
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> best_assign(n + 1);
    int best_satisfied = 0;

    const int NUM_RESTARTS = 50;
    const int MAX_ITER = 1000;

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        vector<int> assign(n + 1);
        for (int v = 1; v <= n; ++v) {
            assign[v] = uniform_int_distribution<int>(0, 1)(rng);
        }

        vector<int> true_count(m, 0);
        int cur_satisfied = 0;
        for (int i = 0; i < m; ++i) {
            auto [a, b, c] = clauses[i];
            int cnt = 0;
            if ((a > 0 && assign[a] == 1) || (a < 0 && assign[-a] == 0)) ++cnt;
            if ((b > 0 && assign[b] == 1) || (b < 0 && assign[-b] == 0)) ++cnt;
            if ((c > 0 && assign[c] == 1) || (c < 0 && assign[-c] == 0)) ++cnt;
            true_count[i] = cnt;
            if (cnt > 0) ++cur_satisfied;
        }

        for (int iter = 0; iter < MAX_ITER; ++iter) {
            if (cur_satisfied == m) break;

            int best_delta = 0;
            int best_v = -1;

            for (int v = 1; v <= n; ++v) {
                int delta = 0;
                for (int idx : pos_clauses[v]) {
                    if (assign[v] == 1) {
                        if (true_count[idx] == 1) --delta;
                    } else {
                        if (true_count[idx] == 0) ++delta;
                    }
                }
                for (int idx : neg_clauses[v]) {
                    if (assign[v] == 0) {
                        if (true_count[idx] == 1) --delta;
                    } else {
                        if (true_count[idx] == 0) ++delta;
                    }
                }
                if (delta > best_delta) {
                    best_delta = delta;
                    best_v = v;
                }
            }

            if (best_delta > 0) {
                assign[best_v] ^= 1;
                for (int idx : pos_clauses[best_v]) {
                    if (assign[best_v] == 1) {
                        ++true_count[idx];
                        if (true_count[idx] == 1) ++cur_satisfied;
                    } else {
                        --true_count[idx];
                        if (true_count[idx] == 0) --cur_satisfied;
                    }
                }
                for (int idx : neg_clauses[best_v]) {
                    if (assign[best_v] == 0) {
                        ++true_count[idx];
                        if (true_count[idx] == 1) ++cur_satisfied;
                    } else {
                        --true_count[idx];
                        if (true_count[idx] == 0) --cur_satisfied;
                    }
                }
            } else {
                vector<int> unsat;
                for (int i = 0; i < m; ++i) {
                    if (true_count[i] == 0) unsat.push_back(i);
                }
                if (unsat.empty()) break;
                int c_idx = unsat[uniform_int_distribution<int>(0, unsat.size() - 1)(rng)];
                auto [a, b, c] = clauses[c_idx];
                int lit_choice = uniform_int_distribution<int>(0, 2)(rng);
                int lit = (lit_choice == 0 ? a : (lit_choice == 1 ? b : c));
                int v = abs(lit);
                assign[v] ^= 1;
                for (int idx : pos_clauses[v]) {
                    if (assign[v] == 1) {
                        ++true_count[idx];
                        if (true_count[idx] == 1) ++cur_satisfied;
                    } else {
                        --true_count[idx];
                        if (true_count[idx] == 0) --cur_satisfied;
                    }
                }
                for (int idx : neg_clauses[v]) {
                    if (assign[v] == 0) {
                        ++true_count[idx];
                        if (true_count[idx] == 1) ++cur_satisfied;
                    } else {
                        --true_count[idx];
                        if (true_count[idx] == 0) --cur_satisfied;
                    }
                }
            }
        }

        if (cur_satisfied > best_satisfied) {
            best_satisfied = cur_satisfied;
            best_assign = assign;
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << best_assign[i] << " \n"[i == n];
    }

    return 0;
}