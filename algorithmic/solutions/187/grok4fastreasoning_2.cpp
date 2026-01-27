#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    bitset<501> adj[501];
    int deg[501] = {0};
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
            deg[u]++;
            deg[v]++;
        }
    }
    // col1: natural order
    int col1[501] = {0};
    int k1 = 0;
    for (int v = 1; v <= N; v++) {
        bool used[501] = {false};
        for (int w = 1; w <= N; w++) {
            if (w == v) continue;
            if (!adj[v][w] && col1[w] != 0) {
                used[col1[w]] = true;
            }
        }
        int c = 1;
        while (c <= N && used[c]) c++;
        col1[v] = c;
        k1 = max(k1, c);
    }
    // col2: degree order (increasing deg_G, i.e., decreasing deg_bar)
    vector<pair<int, int>> nodes;
    for (int i = 1; i <= N; i++) {
        nodes.push_back({deg[i], i});
    }
    sort(nodes.begin(), nodes.end());
    int col2[501] = {0};
    int k2 = 0;
    for (auto& p : nodes) {
        int v = p.second;
        bool used[501] = {false};
        for (int w = 1; w <= N; w++) {
            if (w == v) continue;
            if (!adj[v][w] && col2[w] != 0) {
                used[col2[w]] = true;
            }
        }
        int c = 1;
        while (c <= N && used[c]) c++;
        col2[v] = c;
        k2 = max(k2, c);
    }
    // choose better
    if (k1 <= k2) {
        for (int i = 1; i <= N; i++) cout << col1[i] << endl;
    } else {
        for (int i = 1; i <= N; i++) cout << col2[i] << endl;
    }
    return 0;
}