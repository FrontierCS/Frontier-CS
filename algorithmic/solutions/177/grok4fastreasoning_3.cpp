#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> best_color(n + 1, 0);
    int best_bad = INT_MAX;
    vector<int> vertices(n);
    for (int i = 0; i < n; i++) vertices[i] = i + 1;
    const int TRIES = 20;
    for (int t = 0; t < TRIES; t++) {
        random_shuffle(vertices.begin(), vertices.end());
        vector<int> color(n + 1, 0);
        for (int idx : vertices) {
            vector<int> cnt(4, 0);
            for (int nei : adj[idx]) {
                int c = color[nei];
                if (c != 0) cnt[c]++;
            }
            int minc = INT_MAX;
            int best = 1;
            for (int c = 1; c <= 3; c++) {
                if (cnt[c] < minc || (cnt[c] == minc && c < best)) {
                    minc = cnt[c];
                    best = c;
                }
            }
            color[idx] = best;
        }
        int bad = 0;
        for (int u = 1; u <= n; u++) {
            for (int v : adj[u]) {
                if (v > u && color[u] == color[v]) bad++;
            }
        }
        if (bad < best_bad) {
            best_bad = bad;
            best_color = color;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_color[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}