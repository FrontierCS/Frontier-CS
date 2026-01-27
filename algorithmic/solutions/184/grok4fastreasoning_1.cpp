#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    bitset<1001> adj[1001];
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }
    vector<pair<int, int>> verts;
    for (int i = 1; i <= N; ++i) {
        int d = adj[i].count();
        verts.emplace_back(d, i);
    }
    sort(verts.begin(), verts.end());
    bitset<1001> selected;
    for (auto& p : verts) {
        int v = p.second;
        if ((adj[v] & selected).none()) {
            selected[v] = 1;
        }
    }
    for (int i = 1; i <= N; ++i) {
        cout << (selected[i] ? 1 : 0) << '\n';
    }
    return 0;
}