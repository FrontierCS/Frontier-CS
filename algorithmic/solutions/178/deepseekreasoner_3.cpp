#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<array<pair<int,int>, 3>> clauses(m);
    vector<vector<pair<int,int>>> adj(n+1);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        auto process = [&](int lit) -> pair<int,int> {
            int var = abs(lit);
            int sign = (lit > 0) ? 1 : -1;
            adj[var].push_back({i, sign});
            return {var, sign};
        };
        clauses[i][0] = process(a);
        clauses[i][1] = process(b);
        clauses[i][2] = process(c);
    }

    if (m == 0) {
        for (int i = 1; i <= n; i++) cout << 0 << " ";
        cout << endl;
        return 0;
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> prob(0.0, 1.0);
    uniform_int_distribution<int> rand_bit(0, 1);

    const int NUM_RESTARTS = 100;
    const int MAX_STEPS = 2000;
    const double P = 0.5;

    int best_total = -1;
    vector<int> best_assign(n+1);

    for (int restart = 0; restart < NUM_RESTARTS; restart++) {
        vector<int> assign(n+1);
        for (int i = 1; i <= n; i++) assign[i] = rand_bit(rng);

        vector<int> clause_true_count(m, 0);
        int total_satisfied = 0;
        for (int c = 0; c < m; c++) {
            int cnt = 0;
            for (int j = 0; j < 3; j++) {
                int var = clauses[c][j].first;
                int sign = clauses[c][j].second;
                if ((assign[var] == 1 && sign == 1) || (assign[var] == 0 && sign == -1))
                    cnt++;
            }
            clause_true_count[c] = cnt;
            if (cnt > 0) total_satisfied++;
        }

        for (int step = 0; step < MAX_STEPS; step++) {
            if (total_satisfied == m) break;

            int c;
            int tries = 0;
            do {
                c = uniform_int_distribution<int>(0, m-1)(rng);
            } while (clause_true_count[c] > 0 && ++tries < 1000);
            if (tries == 1000) {
                for (c = 0; c < m; c++) if (clause_true_count[c] == 0) break;
            }

            array<int, 3> vars;
            array<int, 3> deltas;
            int best_delta = -1e9;
            for (int j = 0; j < 3; j++) {
                int var = clauses[c][j].first;
                vars[j] = var;
                int delta = 0;
                int old_val = assign[var];
                int new_val = 1 - old_val;
                for (auto& [clause_idx, sign] : adj[var]) {
                    bool old_literal_true = (old_val == 1 && sign == 1) || (old_val == 0 && sign == -1);
                    bool new_literal_true = (new_val == 1 && sign == 1) || (new_val == 0 && sign == -1);
                    if (old_literal_true && !new_literal_true) {
                        if (clause_true_count[clause_idx] == 1) delta--;
                    } else if (!old_literal_true && new_literal_true) {
                        if (clause_true_count[clause_idx] == 0) delta++;
                    }
                }
                deltas[j] = delta;
                if (delta > best_delta) best_delta = delta;
            }

            int flip_var;
            if (prob(rng) < P) {
                vector<int> candidates;
                for (int j = 0; j < 3; j++) {
                    if (deltas[j] == best_delta) candidates.push_back(vars[j]);
                }
                flip_var = candidates[uniform_int_distribution<int>(0, candidates.size()-1)(rng)];
            } else {
                flip_var = vars[uniform_int_distribution<int>(0,2)(rng)];
            }

            int old_val = assign[flip_var];
            assign[flip_var] = 1 - old_val;
            for (auto& [clause_idx, sign] : adj[flip_var]) {
                bool old_literal_true = (old_val == 1 && sign == 1) || (old_val == 0 && sign == -1);
                bool new_literal_true = (assign[flip_var] == 1 && sign == 1) || (assign[flip_var] == 0 && sign == -1);
                if (old_literal_true && !new_literal_true) {
                    clause_true_count[clause_idx]--;
                    if (clause_true_count[clause_idx] == 0) total_satisfied--;
                } else if (!old_literal_true && new_literal_true) {
                    clause_true_count[clause_idx]++;
                    if (clause_true_count[clause_idx] == 1) total_satisfied++;
                }
            }
        }

        if (total_satisfied > best_total) {
            best_total = total_satisfied;
            best_assign = assign;
        }
    }

    for (int i = 1; i <= n; i++) cout << best_assign[i] << " ";
    cout << endl;
    return 0;
}