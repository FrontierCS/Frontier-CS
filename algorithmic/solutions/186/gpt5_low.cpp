#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<char>> adjMat(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adjMat[u][v] = 1;
        adjMat[v][u] = 1;
    }
    vector<vector<int>> adj(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (adjMat[i][j]) adj[i].push_back(j);
        }
        deg[i] = (int)adj[i].size();
    }

    // DSATUR algorithm
    vector<int> color(N, 0);
    vector<int> satdeg(N, 0);
    int current_max_color = 0;
    vector<vector<char>> usedColors(N, vector<char>(1, 0)); // index 0 unused; will resize as colors grow
    vector<char> colored(N, 0);

    auto ensure_color_size = [&](int cmax){
        for (int i = 0; i < N; ++i) {
            if ((int)usedColors[i].size() <= cmax) usedColors[i].resize(cmax + 1, 0);
        }
    };

    for (int it = 0; it < N; ++it) {
        int best = -1;
        for (int u = 0; u < N; ++u) {
            if (colored[u]) continue;
            if (best == -1 ||
                satdeg[u] > satdeg[best] ||
                (satdeg[u] == satdeg[best] && deg[u] > deg[best]) ||
                (satdeg[u] == satdeg[best] && deg[u] == deg[best] && u < best)) {
                best = u;
            }
        }
        int u = best;
        // find smallest available color
        int c = 1;
        for (; c <= current_max_color; ++c) {
            if ((int)usedColors[u].size() <= c) break;
            if (!usedColors[u][c]) break;
        }
        if (c > current_max_color) {
            current_max_color = c;
            ensure_color_size(current_max_color);
        }
        color[u] = c;
        colored[u] = 1;

        // update neighbors' saturation info
        for (int v : adj[u]) {
            if (colored[v]) continue;
            if ((int)usedColors[v].size() <= c) usedColors[v].resize(c + 1, 0);
            if (!usedColors[v][c]) {
                usedColors[v][c] = 1;
                satdeg[v]++;
            }
        }
    }

    // Simple post-processing: try to reduce colors via greedy recoloring passes
    bool changed = true;
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (color[a] != color[b]) return color[a] > color[b];
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    auto recompute_max = [&](){
        int mx = 0;
        for (int i = 0; i < N; ++i) mx = max(mx, color[i]);
        return mx;
    };

    int maxC = recompute_max();
    vector<char> mark; mark.reserve(N+5);

    // Iterative improvement
    for (int iter = 0; iter < 5; ++iter) { // limit passes
        changed = false;
        maxC = recompute_max();
        for (int targetC = maxC; targetC >= 2; --targetC) {
            // get vertices currently colored targetC, sort by degree desc
            vector<int> verts;
            for (int v = 0; v < N; ++v) if (color[v] == targetC) verts.push_back(v);
            sort(verts.begin(), verts.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return a < b;
            });

            for (int u : verts) {
                // mark neighbor colors
                int limit = targetC - 1;
                if ((int)mark.size() < targetC + 1) mark.assign(targetC + 1, 0);
                else fill(mark.begin(), mark.end(), 0);
                for (int v : adj[u]) {
                    int cv = color[v];
                    if (cv >= 1 && cv <= limit) mark[cv] = 1;
                }
                int newc = 0;
                for (int c = 1; c <= limit; ++c) {
                    if (!mark[c]) { newc = c; break; }
                }
                if (newc) {
                    color[u] = newc;
                    changed = true;
                }
            }
        }
        int newMax = recompute_max();
        if (newMax < maxC) { changed = true; maxC = newMax; }
        if (!changed) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << "\n";
    }
    return 0;
}