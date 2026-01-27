#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> clauses(m, vector<int>(3));
    vector<vector<int>> var_clauses(n + 1);
    for (int j = 0; j < m; j++) {
        set<int> clause_vars;
        for (int k = 0; k < 3; k++) {
            cin >> clauses[j][k];
            int v = abs(clauses[j][k]);
            if (v >= 1 && v <= n) {
                clause_vars.insert(v);
            }
        }
        for (int v : clause_vars) {
            var_clauses[v].push_back(j);
        }
    }
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << " ";
            cout << 0;
        }
        cout << endl;
        return 0;
    }
    auto compute_sat = [&](const vector<int>& ass) -> int {
        int cnt = 0;
        for (int j = 0; j < m; j++) {
            bool sat = false;
            for (int k = 0; k < 3; k++) {
                int l = clauses[j][k];
                int vv = abs(l);
                bool lit = (l > 0 ? ass[vv] : 1 - ass[vv]);
                if (lit) {
                    sat = true;
                    break;
                }
            }
            if (sat) cnt++;
        }
        return cnt;
    };
    auto local_search = [&](vector<int> ass) -> pair<vector<int>, int> {
        int current_sat = compute_sat(ass);
        bool improved = true;
        while (improved) {
            improved = false;
            int max_delta = 0;
            int best_var = -1;
            for (int x = 1; x <= n; x++) {
                int delta = 0;
                for (int j : var_clauses[x]) {
                    bool fixed_sat = false;
                    for (int k = 0; k < 3; k++) {
                        int ll = clauses[j][k];
                        int vvar = abs(ll);
                        if (vvar == x) continue;
                        bool lit_true = (ll > 0 ? ass[vvar] : 1 - ass[vvar]);
                        if (lit_true) {
                            fixed_sat = true;
                            break;
                        }
                    }
                    bool curr_x_cover = false;
                    for (int k = 0; k < 3; k++) {
                        int ll = clauses[j][k];
                        int vvar = abs(ll);
                        if (vvar != x) continue;
                        bool lit_true = (ll > 0 ? ass[x] : 1 - ass[x]);
                        if (lit_true) {
                            curr_x_cover = true;
                            break;
                        }
                    }
                    bool current_clause_sat = fixed_sat || curr_x_cover;
                    bool after_x_cover = false;
                    for (int k = 0; k < 3; k++) {
                        int ll = clauses[j][k];
                        int vvar = abs(ll);
                        if (vvar != x) continue;
                        bool after_lit = (ll > 0 ? (1 - ass[x]) : ass[x]);
                        if (after_lit) {
                            after_x_cover = true;
                            break;
                        }
                    }
                    bool after_clause_sat = fixed_sat || after_x_cover;
                    if (after_clause_sat && !current_clause_sat) delta += 1;
                    if (!after_clause_sat && current_clause_sat) delta -= 1;
                }
                if (delta > max_delta) {
                    max_delta = delta;
                    best_var = x;
                }
            }
            if (max_delta > 0) {
                ass[best_var] = 1 - ass[best_var];
                current_sat += max_delta;
                improved = true;
            }
        }
        return {ass, current_sat};
    };
    vector<int> best_assign(n + 1, 0);
    int best_sat = -1;
    srand(time(NULL));
    int num_trials = 20;
    for (int trial = 0; trial < num_trials; trial++) {
        vector<int> ass(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            ass[i] = rand() % 2;
        }
        auto [new_ass, new_sat] = local_search(ass);
        if (new_sat > best_sat) {
            best_sat = new_sat;
            best_assign = new_ass;
        }
    }
    {
        vector<int> ass(n + 1, 0);
        auto [new_ass, new_sat] = local_search(ass);
        if (new_sat > best_sat) {
            best_sat = new_sat;
            best_assign = new_ass;
        }
    }
    {
        vector<int> ass(n + 1, 1);
        auto [new_ass, new_sat] = local_search(ass);
        if (new_sat > best_sat) {
            best_sat = new_sat;
            best_assign = new_ass;
        }
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best_assign[i];
    }
    cout << endl;
    return 0;
}