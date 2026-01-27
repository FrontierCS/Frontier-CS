#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(0));
    int n, m;
    cin >> n >> m;
    vector<pair<int, int>> clauses;
    vector<vector<pair<int, int>>> inc(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        clauses.emplace_back(a, b);
        int va = abs(a), vb = abs(b);
        inc[va].emplace_back(b, a > 0 ? 1 : -1);
        inc[vb].emplace_back(a, b > 0 ? 1 : -1);
    }
    vector<int> best_assignment(n + 1);
    int best_satisfied = -1;
    int num_trials = 20;
    for (int trial = 0; trial < num_trials; trial++) {
        vector<int> val(n + 1);
        for (int i = 1; i <= n; i++) {
            val[i] = rand() % 2;
        }
        int cur_s = 0;
        for (auto cl : clauses) {
            int a = cl.first, b = cl.second;
            int va = abs(a), vb = abs(b);
            bool la = (a > 0 ? val[va] : 1 - val[va]);
            bool lb = (b > 0 ? val[vb] : 1 - val[vb]);
            if (la || lb) cur_s++;
        }
        vector<int> d(n + 1, 0);
        for (int v = 1; v <= n; v++) {
            int dd = 0;
            for (auto p : inc[v]) {
                int o_lit = p.first;
                int pol = p.second;
                int ov = abs(o_lit);
                bool other_cur = (o_lit > 0 ? val[ov] : 1 - val[ov]);
                bool l_cur = (pol > 0 ? val[v] : 1 - val[v]);
                if (other_cur) continue;
                dd += (l_cur ? -1 : 1);
            }
            d[v] = dd;
        }
        int iters = 0;
        const int max_iters = 10000;
        while (true) {
            iters++;
            if (iters > max_iters) break;
            int best_d = 0;
            int bv = -1;
            for (int vv = 1; vv <= n; vv++) {
                if (d[vv] > best_d) {
                    best_d = d[vv];
                    bv = vv;
                }
            }
            if (best_d <= 0) break;
            int old_valv = val[bv];
            int old_dv = best_d;
            val[bv] = 1 - old_valv;
            cur_s += old_dv;
            d[bv] = -old_dv;
            for (auto p : inc[bv]) {
                int o_lit = p.first;
                int pol_v = p.second;
                int w = abs(o_lit);
                if (w == bv) continue;
                int pol_w = (o_lit > 0 ? 1 : -1);
                bool l_w_cur = (pol_w > 0 ? val[w] : 1 - val[w]);
                bool old_other_w = (pol_v > 0 ? old_valv : 1 - old_valv);
                int old_c = old_other_w ? 0 : (l_w_cur ? -1 : 1);
                bool new_other_w = (pol_v > 0 ? val[bv] : 1 - val[bv]);
                int new_c = new_other_w ? 0 : (l_w_cur ? -1 : 1);
                int ch = new_c - old_c;
                d[w] += ch;
            }
        }
        if (cur_s > best_satisfied) {
            best_satisfied = cur_s;
            best_assignment = val;
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
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best_assignment[i];
    }
    cout << endl;
    return 0;
}