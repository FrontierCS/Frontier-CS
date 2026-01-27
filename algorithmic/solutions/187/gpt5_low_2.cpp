#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    
    vector<vector<char>> adj(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u][v] = adj[v][u] = 1;
    }
    
    // Build complement graph neighbors
    vector<vector<int>> compNei(N);
    vector<int> degComp(N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!adj[i][j]) {
                compNei[i].push_back(j);
                compNei[j].push_back(i);
            }
        }
        degComp[i] = (int)compNei[i].size();
    }
    
    vector<int> color(N, 0);
    vector<char> uncolored(N, 1);
    vector<int> satDeg(N, 0);
    // colors used by complement neighbors (for DSATUR)
    vector<vector<char>> colorUsed(N, vector<char>(N + 2, 0)); // colors 1..N
    
    int K = 0;
    
    // Select initial vertex: maximum degree in complement
    int first = 0;
    for (int i = 1; i < N; ++i) {
        if (degComp[i] > degComp[first]) first = i;
    }
    
    for (int step = 0; step < N; ++step) {
        int u;
        if (step == 0) {
            u = first;
        } else {
            // select vertex with max saturation degree, tie by complement degree
            int best = -1;
            int bestSat = -1, bestDeg = -1;
            for (int i = 0; i < N; ++i) if (uncolored[i]) {
                int s = satDeg[i];
                int d = degComp[i];
                if (s > bestSat || (s == bestSat && d > bestDeg)) {
                    bestSat = s;
                    bestDeg = d;
                    best = i;
                }
            }
            u = best;
        }
        
        // assign smallest feasible color
        int c = 1;
        while (c <= K && colorUsed[u][c]) ++c;
        if (c > K) K = c;
        color[u] = c;
        uncolored[u] = 0;
        
        // update neighbors in complement
        for (int v : compNei[u]) if (uncolored[v]) {
            if (!colorUsed[v][c]) {
                colorUsed[v][c] = 1;
                satDeg[v]++;
            }
        }
    }
    
    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}