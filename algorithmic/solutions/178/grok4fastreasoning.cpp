#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    vector<vector<int>> clauses(m, vector<int>(3));
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < 3; j++) {
            cin >> clauses[i][j];
        }
    }
    auto evaluate = [&](const vector<int>& x) -> int {
        int sat = 0;
        for (const auto& c : clauses) {
            bool ok = false;
            for (int l : c) {
                int v = abs(l);
                bool lit = (l > 0) ? (x[v] == 1) : (x[v] == 0);
                if (lit) {
                    ok = true;
                    break;
                }
            }
            if (ok) sat++;
        }
        return sat;
    };
    vector<int> best_x(n + 1, 0);
    int best_sat = evaluate(best_x);
    const int TRIALS = 100;
    for (int t = 0; t < TRIALS; t++) {
        vector<int> x(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            x[i] = rand() % 2;
        }
        int cur_sat = evaluate(x);
        bool improved = true;
        while (improved) {
            improved = false;
            int max_sat = cur_sat;
            int flip_v = -1;
            for (int v = 1; v <= n; v++) {
                x[v] = 1 - x[v];
                int temp_sat = evaluate(x);
                x[v] = 1 - x[v];
                if (temp_sat > max_sat) {
                    max_sat = temp_sat;
                    flip_v = v;
                }
            }
            if (flip_v != -1) {
                x[flip_v] = 1 - x[flip_v];
                cur_sat = max_sat;
                improved = true;
            }
        }
        if (cur_sat > best_sat) {
            best_sat = cur_sat;
            best_x = x;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_x[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}