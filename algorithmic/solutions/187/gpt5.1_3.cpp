#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector< bitset<MAXN> > g(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].set(v);
        g[v].set(u);
    }

    // Build complement graph adjacency list
    vector<vector<int>> compAdj(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!g[i].test(j)) {
                compAdj[i].push_back(j);
                compAdj[j].push_back(i);
            }
        }
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)compAdj[i].size();

    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    vector< bitset<MAXN + 1> > neighColors(N); // colors of neighbors in complement
    int maxColor = 0;

    for (int coloredCount = 0; coloredCount < N; ++coloredCount) {
        int u = -1;
        int bestSat = -1, bestDeg = -1;

        // Select vertex with maximum saturation, break ties by degree
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            if (sat[i] > bestSat || (sat[i] == bestSat && deg[i] > bestDeg)) {
                bestSat = sat[i];
                bestDeg = deg[i];
                u = i;
            }
        }

        // Assign the smallest feasible color
        bitset<MAXN + 1> &nc = neighColors[u];
        int c;
        for (c = 1; c <= maxColor; ++c) {
            if (!nc.test(c)) break;
        }
        if (c > maxColor) maxColor = c;
        color[u] = c;

        // Update saturation of neighbors in complement graph
        for (int v : compAdj[u]) {
            if (color[v] == 0) {
                if (!neighColors[v].test(c)) {
                    neighColors[v].set(c);
                    sat[v]++;
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }

    return 0;
}