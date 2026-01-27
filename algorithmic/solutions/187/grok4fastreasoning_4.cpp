#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    static bool adj[501][501];
    memset(adj, 0, sizeof(adj));
    vector<int> degG(N + 1, 0);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (!adj[u][v]) {
            adj[u][v] = adj[v][u] = true;
            degG[u]++;
            degG[v]++;
        }
    }
    vector<int> color(N + 1, 0);
    for (int step = 0; step < N; step++) {
        int best_v = -1;
        int max_sat = -1;
        int best_degbar = -1;
        int best_id = INT_MAX;
        for (int v = 1; v <= N; v++) {
            if (color[v] != 0) continue;
            bool seen[501] = {false};
            int sat = 0;
            for (int w = 1; w <= N; w++) {
                if (color[w] == 0 || w == v) continue;
                if (!adj[v][w]) {
                    int cc = color[w];
                    if (!seen[cc]) {
                        seen[cc] = true;
                        sat++;
                    }
                }
            }
            int degbar = N - 1 - degG[v];
            bool better = false;
            if (sat > max_sat) better = true;
            else if (sat == max_sat) {
                if (degbar > best_degbar) better = true;
                else if (degbar == best_degbar) {
                    if (v < best_id) better = true;
                }
            }
            if (better) {
                max_sat = sat;
                best_degbar = degbar;
                best_id = v;
                best_v = v;
            }
        }
        // color best_v
        bool forbidden[501] = {false};
        for (int w = 1; w <= N; w++) {
            if (color[w] == 0 || w == best_v) continue;
            if (!adj[best_v][w]) {
                forbidden[color[w]] = true;
            }
        }
        int c = 1;
        while (forbidden[c]) c++;
        color[best_v] = c;
    }
    for (int i = 1; i <= N; i++) {
        cout << color[i] << endl;
    }
    return 0;
}