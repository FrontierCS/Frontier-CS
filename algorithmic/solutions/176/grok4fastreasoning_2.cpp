#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> clauses(m, vector<int>(3));
    vector<vector<pair<int, int>>> var_clauses(n + 1);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < 3; j++) {
            cin >> clauses[i][j];
            int lit = clauses[i][j];
            int v = abs(lit);
            if (v >= 1 && v <= n) {
                var_clauses[v].emplace_back(i, j);
            }
        }
    }
    srand(time(NULL));
    vector<int> best_assign(n + 1);
    int best_s = -1;
    vector<int> assign(n + 1);
    const int num_restarts = 20;
    const int max_passes = 200;
    for (int restart = 0; restart < num_restarts; restart++) {
        for (int i = 1; i <= n; i++) {
            assign[i] = rand() % 2;
        }
        int passes = 0;
        bool changed = true;
        while (changed && passes < max_passes) {
            changed = false;
            passes++;
            for (int v = 1; v <= n; v++) {
                int delta = 0;
                for (auto [cid, pos] : var_clauses[v]) {
                    const vector<int>& cl = clauses[cid];
                    int lit_x = cl[pos];
                    bool val_x = (lit_x > 0 ? assign[v] : 1 - assign[v]);
                    bool other_sat = false;
                    for (int k = 0; k < 3; k++) {
                        if (k == pos) continue;
                        int ll = cl[k];
                        int vv = abs(ll);
                        bool val = (ll > 0 ? assign[vv] : 1 - assign[vv]);
                        if (val) {
                            other_sat = true;
                            break;
                        }
                    }
                    if (other_sat) continue;
                    if (val_x) {
                        delta--;
                    } else {
                        delta++;
                    }
                }
                if (delta > 0) {
                    assign[v] = 1 - assign[v];
                    changed = true;
                }
            }
        }
        int s = 0;
        for (const auto& cl : clauses) {
            bool sat = false;
            for (int ll : cl) {
                int vv = abs(ll);
                bool val = (ll > 0 ? assign[vv] : 1 - assign[vv]);
                if (val) {
                    sat = true;
                    break;
                }
            }
            if (sat) s++;
        }
        if (s > best_s) {
            best_s = s;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_assign[i];
        if (i < n) cout << " ";
        else cout << endl;
    }
    return 0;
}