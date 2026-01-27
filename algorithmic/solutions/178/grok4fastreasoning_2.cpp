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
    vector<vector<pair<int, bool>>> appears(n + 1);
    for (int c = 0; c < m; c++) {
        for (int k = 0; k < 3; k++) {
            int lit = clauses[c][k];
            int v = abs(lit);
            bool posi = lit > 0;
            appears[v].emplace_back(c, posi);
        }
    }
    vector<char> best_assign(n + 1, 0);
    int max_sat = -1;
    vector<int> true_count(m);
    vector<char> assign(n + 1);
    int num_restarts = (m == 0 ? 1 : 100);
    for (int r = 0; r < num_restarts; r++) {
        for (int i = 1; i <= n; i++) {
            if (m > 0) assign[i] = rand() % 2;
            else assign[i] = 0;
        }
        for (int c = 0; c < m; c++) {
            int cnt = 0;
            for (int k = 0; k < 3; k++) {
                int lit = clauses[c][k];
                int v = abs(lit);
                bool posi = lit > 0;
                bool cur_val = (assign[v] == 1);
                bool ltrue = posi ? cur_val : !cur_val;
                if (ltrue) cnt++;
            }
            true_count[c] = cnt;
        }
        int cur_sat = 0;
        for (int c = 0; c < m; c++) {
            if (true_count[c] > 0) cur_sat++;
        }
        bool changed = true;
        while (changed) {
            changed = false;
            int best_d = 0;
            int best_v = -1;
            map<int, int> best_delta_c;
            for (int v = 1; v <= n; v++) {
                map<int, int> delta_c;
                for (auto p : appears[v]) {
                    int c = p.first;
                    bool posi = p.second;
                    bool cur_val = (assign[v] == 1);
                    bool ltrue = posi ? cur_val : !cur_val;
                    int d = ltrue ? -1 : 1;
                    delta_c[c] += d;
                }
                int this_d = 0;
                for (auto& pp : delta_c) {
                    int c = pp.first;
                    int dc = pp.second;
                    int oldc = true_count[c];
                    bool os = oldc > 0;
                    int nc = oldc + dc;
                    bool ns = nc > 0;
                    if (os && !ns) this_d -= 1;
                    else if (!os && ns) this_d += 1;
                }
                if (this_d > best_d) {
                    best_d = this_d;
                    best_v = v;
                    best_delta_c = delta_c;
                }
            }
            if (best_d > 0) {
                changed = true;
                for (auto& pp : best_delta_c) {
                    true_count[pp.first] += pp.second;
                }
                assign[best_v] = 1 - assign[best_v];
                cur_sat += best_d;
            }
        }
        if (cur_sat > max_sat) {
            max_sat = cur_sat;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << (int)best_assign[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}