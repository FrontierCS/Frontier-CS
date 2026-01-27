#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;
const int MAXC = 501; // colors 1..500

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    vector<bitset<MAXN>> mat(N);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    vector<int> color(N, 0);
    vector<int> degree(N);
    for (int i = 0; i < N; ++i) degree[i] = (int)adj[i].size();

    vector<int> sat_deg(N, 0);
    vector<bitset<MAXC>> neigh_colors(N); // colors used by neighbors

    int colored = 0;
    int max_color = 0;

    while (colored < N) {
        int best_v = -1;
        int best_sat = -1;
        int best_deg = -1;

        for (int v = 0; v < N; ++v) {
            if (color[v] == 0) {
                if (sat_deg[v] > best_sat ||
                    (sat_deg[v] == best_sat && degree[v] > best_deg)) {
                    best_sat = sat_deg[v];
                    best_deg = degree[v];
                    best_v = v;
                }
            }
        }

        int v = best_v;
        int c;
        for (c = 1; c <= max_color; ++c) {
            if (!neigh_colors[v].test(c)) break;
        }
        if (c == max_color + 1) {
            max_color++;
        }
        color[v] = c;
        ++colored;

        for (int u : adj[v]) {
            if (color[u] == 0) {
                if (!neigh_colors[u].test(c)) {
                    neigh_colors[u].set(c);
                    sat_deg[u]++;
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }

    return 0;
}