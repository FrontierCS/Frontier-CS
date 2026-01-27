#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<vector<int>> states;
    states.push_back(init);
    vector<int> cur = init;
    const int MAX_STEPS = 20000;

    for (int step = 0; step < MAX_STEPS && cur != target; ++step) {
        vector<int> nxt = cur;
        bool changed = false;
        for (int v = 0; v < n; ++v) {
            int desired = target[v];
            if (cur[v] == desired) continue;
            bool has = false;
            if (cur[v] == desired) has = true;
            else {
                for (int u : adj[v]) {
                    if (cur[u] == desired) {
                        has = true;
                        break;
                    }
                }
            }
            if (has) {
                nxt[v] = desired;
                if (!changed && nxt[v] != cur[v]) changed = true;
            }
        }
        if (!changed) break;
        states.push_back(nxt);
        cur.swap(nxt);
    }

    // Assuming problem guarantee ensures cur == target here
    int k = (int)states.size() - 1;
    cout << k << "\n";
    for (auto &st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }

    return 0;
}