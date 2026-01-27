#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N + 1);
    vector<int> degree(N + 1, 0);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    vector<pair<int, int>> verts;
    for (int i = 1; i <= N; i++) {
        verts.push_back({degree[i], i});
    }
    sort(verts.begin(), verts.end());
    vector<bool> selected(N + 1, false);
    for (auto& p : verts) {
        int cand = p.second;
        bool can_add = true;
        for (int nei : adj[cand]) {
            if (selected[nei]) {
                can_add = false;
                break;
            }
        }
        if (can_add) {
            selected[cand] = true;
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << (selected[i] ? 1 : 0) << '\n';
    }
    return 0;
}