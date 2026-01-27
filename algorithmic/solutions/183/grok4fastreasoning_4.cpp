#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
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
    vector<int> sel(N + 1, 0);
    for (auto& p : order) {
        int v = p.second;
        bool ok = true;
        for (int u : adj[v]) {
            if (sel[u]) {
                ok = false;
                break;
            }
        }
        if (ok) sel[v] = 1;
    }
    for (int i = 1; i <= N; i++) {
        cout << sel[i] << '\n';
    }
    return 0;
}