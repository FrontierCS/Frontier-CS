#include <bits/stdc++.h>
using namespace std;

int compute_sat(const vector<int>& assign, const vector<vector<int>>& clauses, int m) {
    int cnt = 0;
    for (int i = 0; i < m; ++i) {
        bool ok = false;
        for (int ll : clauses[i]) {
            int v = abs(ll);
            bool tr = (ll > 0 ? assign[v] : assign[v] == 0);
            if (tr) {
                ok = true;
                break;
            }
        }
        if (ok) ++cnt;
    }
    return cnt;
}

int compute_delta(int x, const vector<int>& assign, const vector<vector<int>>& clauses, const vector<vector<int>>& var_clauses) {
    int val = assign[x];
    int newval = 1 - val;
    int delta = 0;
    for (int cl : var_clauses[x]) {
        bool was = false;
        for (int ll : clauses[cl]) {
            int v = abs(ll);
            int av = (v == x ? val : assign[v]);
            bool tr = (ll > 0 ? av == 1 : av == 0);
            if (tr) {
                was = true;
                break;
            }
        }
        bool aft = false;
        for (int ll : clauses[cl]) {
            int v = abs(ll);
            int av = (v == x ? newval : assign[v]);
            bool tr = (ll > 0 ? av == 1 : av == 0);
            if (tr) {
                aft = true;
                break;
            }
        }
        if (was && !aft) --delta;
        else if (!was && aft) ++delta;
    }
    return delta;
}

pair<int, vector<int>> hill_climb(vector<int> assign, const vector<vector<int>>& clauses, const vector<vector<int>>& var_clauses, int n, int m) {
    int sat = compute_sat(assign, clauses, m);
    const int MAX_ITER = 10000;
    int iter = 0;
    while (iter++ < MAX_ITER) {
        int max_d = 0;
        int best_x = -1;
        for (int x = 1; x <= n; ++x) {
            int d = compute_delta(x, assign, clauses, var_clauses);
            if (d > max_d) {
                max_d = d;
                best_x = x;
            }
        }
        if (max_d <= 0) break;
        assign[best_x] = 1 - assign[best_x];
        sat += max_d;
    }
    return {sat, assign};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> clauses(m, vector<int>(3));
    vector<vector<int>> var_clauses(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int va = abs(a), vb = abs(b), vc = abs(c);
        var_clauses[va].push_back(i);
        if (vb != va) var_clauses[vb].push_back(i);
        if (vc != va && vc != vb) var_clauses[vc].push_back(i);
    }
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0;
            if (i < n) cout << " ";
            else cout << "\n";
        }
        return 0;
    }
    int best_s = -1;
    vector<int> best_a(n + 1);
    auto try_start = [&](vector<int> init) {
        auto [sat, ass] = hill_climb(init, clauses, var_clauses, n, m);
        if (sat > best_s) {
            best_s = sat;
            best_a = ass;
        }
    };
    vector<int> all0(n + 1, 0);
    try_start(all0);
    vector<int> all1(n + 1, 1);
    try_start(all1);
    srand(time(NULL));
    const int NUM_RESTARTS = 10;
    for (int r = 0; r < NUM_RESTARTS; ++r) {
        vector<int> randa(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            randa[i] = rand() % 2;
        }
        try_start(randa);
    }
    for (int i = 1; i <= n; ++i) {
        cout << best_a[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}