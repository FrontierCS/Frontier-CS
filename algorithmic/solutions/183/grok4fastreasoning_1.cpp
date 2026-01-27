#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    vector<int> deg(N + 1, 0);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }
    vector<pair<int, int>> order;
    for (int i = 1; i <= N; i++) {
        order.emplace_back(deg[i], i);
    }
    sort(order.begin(), order.end());
    vector<int> selected(N + 1, 0);
    for (auto& p : order) {
        int u = p.second;
        bool can = true;
        for (int v : adj[u]) {
            if (selected[v]) {
                can = false;
                break;
            }
        }
        if (can) {
            selected[u] = 1;
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << selected[i] << '\n';
    }
    return 0;
}