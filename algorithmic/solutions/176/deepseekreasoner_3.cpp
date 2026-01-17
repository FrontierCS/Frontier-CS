#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) cout << "0 ";
        cout << endl;
        return 0;
    }

    vector<array<int, 3>> clauses(m);
    vector<vector<int>> pos(n + 1), neg(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        for (int lit : {a, b, c}) {
            int var = abs(lit);
            if (lit > 0) pos[var].push_back(i);
            else         neg[var].push_back(i);
        }
    }

    const int NUM_RESTARTS = 20;
    int best_total = 0;
    vector<bool> best_assignment(n + 1);

    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> binary(0, 1);

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        // random initial assignment
        vector<bool> assignment(n + 1);
        for (int i = 1; i <= n; ++i) assignment[i] = binary(rng);

        // compute true_count for each clause and total satisfied
        vector<int> true_count(m, 0);
        for (int i = 0; i < m; ++i) {
            for (int lit : clauses[i]) {
                bool lit_true = (lit > 0) ? assignment[lit] : !assignment[-lit];
                if (lit_true) true_count[i]++;
            }
        }
        int total_sat = 0;
        for (int i = 0; i < m; ++i) if (true_count[i] > 0) total_sat++;

        // function to compute gain for a variable
        auto compute_gain = [&](int v) -> int {
            int gain = 0;
            // positive occurrences
            for (int j : pos[v]) {
                int old_t = true_count[j];
                int new_t = old_t + (assignment[v] ? -1 : 1);
                if (old_t == 0 && new_t >= 1) gain++;
                else if (old_t == 1 && new_t == 0) gain--;
            }
            // negative occurrences
            for (int j : neg[v]) {
                int old_t = true_count[j];
                int new_t = old_t + (assignment[v] ? 1 : -1);
                if (old_t == 0 && new_t >= 1) gain++;
                else if (old_t == 1 && new_t == 0) gain--;
            }
            return gain;
        };

        // initial gains
        vector<int> gain(n + 1);
        for (int v = 1; v <= n; ++v) gain[v] = compute_gain(v);

        // data structures for incremental updates
        vector<bool> need_update(n + 1, false);
        vector<int> to_update;
        auto add_var = [&](int var) {
            if (!need_update[var]) {
                need_update[var] = true;
                to_update.push_back(var);
            }
        };

        // hill climbing
        while (true) {
            int best_var = -1, best_gain = 0;
            for (int v = 1; v <= n; ++v) {
                if (gain[v] > best_gain) {
                    best_gain = gain[v];
                    best_var = v;
                }
            }
            if (best_var == -1) break; // no improving flip

            int v = best_var;
            add_var(v);

            // process clauses where v appears positively
            for (int j : pos[v]) {
                int old_t = true_count[j];
                int new_t = old_t + (assignment[v] ? -1 : 1);
                true_count[j] = new_t;
                if (old_t == 0 && new_t >= 1) total_sat++;
                else if (old_t == 1 && new_t == 0) total_sat--;
                // mark other variables in this clause
                for (int lit : clauses[j]) {
                    int var = abs(lit);
                    if (var != v) add_var(var);
                }
            }
            // process clauses where v appears negatively
            for (int j : neg[v]) {
                int old_t = true_count[j];
                int new_t = old_t + (assignment[v] ? 1 : -1);
                true_count[j] = new_t;
                if (old_t == 0 && new_t >= 1) total_sat++;
                else if (old_t == 1 && new_t == 0) total_sat--;
                for (int lit : clauses[j]) {
                    int var = abs(lit);
                    if (var != v) add_var(var);
                }
            }

            // flip the variable
            assignment[v] = !assignment[v];

            // recompute gains for affected variables
            for (int var : to_update) {
                gain[var] = compute_gain(var);
                need_update[var] = false;
            }
            to_update.clear();

            if (total_sat == m) break; // all satisfied
        }

        if (total_sat > best_total) {
            best_total = total_sat;
            best_assignment = assignment;
            if (best_total == m) break; // optimal found
        }
    }

    // output the best assignment
    for (int i = 1; i <= n; ++i) {
        cout << (best_assignment[i] ? 1 : 0) << " ";
    }
    cout << endl;

    return 0;
}