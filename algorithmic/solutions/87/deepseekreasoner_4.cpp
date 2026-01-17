#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    cin >> n >> m;
    vector<int> initial(n), target(n);
    for (int i = 0; i < n; i++) cin >> initial[i];
    for (int i = 0; i < n; i++) cin >> target[i];
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<vector<int>> sequence;
    sequence.push_back(initial);
    vector<int> cur = initial;
    int steps = 0;
    const int MAX_STEPS = 20000;
    while (cur != target && steps < MAX_STEPS) {
        vector<int> nxt = cur;
        bool changed = false;
        for (int v = 0; v < n; v++) {
            if (cur[v] == target[v]) {
                nxt[v] = cur[v];
                continue;
            }
            bool found = false;
            if (cur[v] == target[v]) found = true;
            for (int u : adj[v]) {
                if (cur[u] == target[v]) {
                    found = true;
                    break;
                }
            }
            if (found) {
                nxt[v] = target[v];
                changed = true;
            } else {
                nxt[v] = cur[v];
            }
        }
        if (!changed) break;
        cur = nxt;
        sequence.push_back(cur);
        steps++;
    }
    cout << steps << "\n";
    for (const auto& state : sequence) {
        for (int i = 0; i < n; i++) {
            cout << state[i] << " \n"[i == n-1];
        }
    }
    return 0;
}