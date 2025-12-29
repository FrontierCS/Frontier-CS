#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(n + 1);
    for (int i = 1; i <= n; i++) {
        deg[i] = adj[i].size();
    }
    vector<pair<int, int>> sorter(n);
    for (int i = 1; i <= n; i++) {
        sorter[i - 1] = {-deg[i], i};
    }
    sort(sorter.begin(), sorter.end());
    vector<int> order(n);
    for (int i = 0; i < n; i++) {
        order[i] = sorter[i].second;
    }
    vector<int> best_color(n + 1, 0);
    int min_bad = INT_MAX;
    auto do_greedy = [&](const vector<int>& ord) -> pair<vector<int>, int> {
        vector<int> col(n + 1, 0);
        for (int v : ord) {
            vector<int> conf(4, 0);
            for (int u : adj[v]) {
                if (col[u] != 0) {
                    conf[col[u]]++;
                }
            }
            int best_c = 1;
            int mc = conf[1];
            for (int c = 2; c <= 3; c++) {
                if (conf[c] < mc) {
                    mc = conf[c];
                    best_c = c;
                }
            }
            col[v] = best_c;
        }
        int bad = 0;
        for (int u = 1; u <= n; u++) {
            for (int vv : adj[u]) {
                int v = vv;
                if (v > u && col[u] == col[v]) {
                    bad++;
                }
            }
        }
        return {col, bad};
    };
    // Degree order
    pair<vector<int>, int> res = do_greedy(order);
    vector<int> col = res.first;
    int bad = res.second;
    min_bad = bad;
    best_color = col;
    // Random trials
    srand(time(NULL));
    const int TRIALS = 20;
    for (int t = 0; t < TRIALS; t++) {
        vector<int> rorder(n);
        for (int i = 0; i < n; i++) {
            rorder[i] = i + 1;
        }
        random_shuffle(rorder.begin(), rorder.end());
        res = do_greedy(rorder);
        col = res.first;
        bad = res.second;
        if (bad < min_bad) {
            min_bad = bad;
            best_color = col;
        }
    }
    // Output
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best_color[i];
    }
    cout << "\n";
}