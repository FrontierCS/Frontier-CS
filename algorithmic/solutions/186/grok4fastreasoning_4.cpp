#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(N + 1, 0);
    for (int i = 1; i <= N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].resize(it - adj[i].begin());
        deg[i] = adj[i].size();
    }
    vector<pair<int, int>> nodes;
    for (int i = 1; i <= N; i++) {
        nodes.emplace_back(-deg[i], i);
    }
    sort(nodes.begin(), nodes.end());
    vector<int> color(N + 1, 0);
    for (auto& p : nodes) {
        int v = p.second;
        set<int> used;
        for (int nei : adj[v]) {
            if (color[nei] != 0) used.insert(color[nei]);
        }
        int col = 1;
        while (used.count(col)) col++;
        color[v] = col;
    }
    for (int i = 1; i <= N; i++) {
        cout << color[i] << '\n';
    }
    return 0;
}