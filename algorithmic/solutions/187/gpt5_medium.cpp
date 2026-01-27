#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<char>> G(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        G[u][v] = 1;
        G[v][u] = 1;
    }

    // Build complement graph adjacency list
    vector<vector<int>> comp_adj(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!G[i][j]) {
                comp_adj[i].push_back(j);
                comp_adj[j].push_back(i);
            }
        }
    }

    vector<int> color(N, 0);
    vector<int> sat_cnt(N, 0);
    vector<int> degree(N, 0);
    for (int i = 0; i < N; ++i) degree[i] = (int)comp_adj[i].size();

    // sat_used[v][c] = whether color c appears among complement neighbors of v
    vector<vector<char>> sat_used(N, vector<char>(N + 1, 0));
    vector<char> colored(N, 0);

    int K = 0;
    for (int step = 0; step < N; ++step) {
        // Select vertex with maximum saturation, tie by degree, then by index
        int best = -1;
        int best_sat = -1, best_deg = -1;
        for (int v = 0; v < N; ++v) {
            if (colored[v]) continue;
            int s = sat_cnt[v];
            int d = degree[v];
            if (s > best_sat || (s == best_sat && d > best_deg) || (s == best_sat && d == best_deg && v < best)) {
                best_sat = s;
                best_deg = d;
                best = v;
            }
        }

        int v = best;
        // Assign the smallest available color
        int c = 1;
        while (c <= K && sat_used[v][c]) ++c;
        if (c == K + 1) K = c;
        color[v] = c;
        colored[v] = 1;

        // Update saturation of neighbors in complement graph
        for (int u : comp_adj[v]) {
            if (colored[u]) continue;
            if (!sat_used[u][c]) {
                sat_used[u][c] = 1;
                sat_cnt[u]++;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << "\n";
    }

    return 0;
}