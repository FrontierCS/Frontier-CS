#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<array<int, 3>> clauses(m);
    vector<vector<pair<int, int>>> appears(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; k++) {
            int l = lits[k];
            int v = abs(l);
            appears[v].emplace_back(i, l);
        }
    }
    vector<int> deg(n + 1);
    for (int i = 1; i <= n; i++) {
        deg[i] = appears[i].size();
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int i, int j) {
        return deg[i] > deg[j];
    });
    vector<int> ass(n + 1, -1);
    for (int idx = 0; idx < n; idx++) {
        int x = order[idx];
        int gain[2] = {0, 0};
        for (auto [j, l] : appears[x]) {
            bool already = false;
            auto& cls = clauses[j];
            for (int k = 0; k < 3; k++) {
                int ll = cls[k];
                int vv = abs(ll);
                if (vv == x) continue;
                if (ass[vv] != -1) {
                    bool lit = (ll > 0 ? ass[vv] == 1 : ass[vv] == 0);
                    if (lit) {
                        already = true;
                        break;
                    }
                }
            }
            if (already) continue;
            for (int val = 0; val < 2; val++) {
                bool lit = (l > 0 ? val == 1 : val == 0);
                if (lit) gain[val]++;
            }
        }
        int chosen = (gain[0] >= gain[1] ? 0 : 1);
        ass[x] = chosen;
    }
    // Local search
    for (int iter = 0; iter < 100; iter++) {
        bool changed = false;
        for (int x = 1; x <= n; x++) {
            int delta = 0;
            int cur_val = ass[x];
            for (auto [j, l] : appears[x]) {
                bool was_lit = (l > 0 ? cur_val == 1 : cur_val == 0);
                bool other_sat = false;
                auto& cls = clauses[j];
                for (int k = 0; k < 3; k++) {
                    int ll = cls[k];
                    int vv = abs(ll);
                    if (vv == x) continue;
                    bool lit = (ll > 0 ? ass[vv] == 1 : ass[vv] == 0);
                    if (lit) {
                        other_sat = true;
                        break;
                    }
                }
                if (!other_sat) {
                    if (was_lit) delta--;
                    else delta++;
                }
            }
            if (delta > 0) {
                ass[x] = 1 - cur_val;
                changed = true;
            }
        }
        if (!changed) break;
    }
    for (int i = 1; i <= n; i++) {
        cout << ass[i];
        if (i < n) cout << " ";
        else cout << '\n';
    }
    return 0;
}