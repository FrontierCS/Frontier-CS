#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;

bool adj[MAXN + 1][MAXN + 1];
int degreeG[MAXN + 1];
int degComp[MAXN + 1];
int colorOf[MAXN + 1];
int sat[MAXN + 1];
bitset<MAXN + 1> neighborColors[MAXN + 1];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    for (int i = 1; i <= N; ++i) {
        degreeG[i] = 0;
        colorOf[i] = 0;
        sat[i] = 0;
        neighborColors[i].reset();
        for (int j = 1; j <= N; ++j) {
            adj[i][j] = false;
        }
    }

    for (int k = 0; k < M; ++k) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        if (!adj[u][v]) {
            adj[u][v] = adj[v][u] = true;
            degreeG[u]++;
            degreeG[v]++;
        }
    }

    for (int i = 1; i <= N; ++i) {
        degComp[i] = (N - 1) - degreeG[i];
    }

    int K = 0; // number of colors used

    for (int iter = 0; iter < N; ++iter) {
        // Select uncolored vertex with maximum saturation degree, tie by complement degree
        int v = -1;
        int bestSat = -1;
        int bestDeg = -1;
        for (int i = 1; i <= N; ++i) {
            if (colorOf[i] == 0) {
                if (sat[i] > bestSat || (sat[i] == bestSat && degComp[i] > bestDeg)) {
                    bestSat = sat[i];
                    bestDeg = degComp[i];
                    v = i;
                }
            }
        }

        // Determine color for v
        bitset<MAXN + 1> forbidden = neighborColors[v];
        int c = 1;
        while (c <= K && forbidden.test(c)) ++c;
        if (c > K) {
            ++K;
            c = K;
        }
        colorOf[v] = c;

        // Update saturation of neighbors in complement graph
        for (int u = 1; u <= N; ++u) {
            if (u == v) continue;
            if (colorOf[u] != 0) continue;
            if (!adj[v][u]) { // edge in complement
                if (!neighborColors[u].test(c)) {
                    neighborColors[u].set(c);
                    sat[u]++;
                }
            }
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << colorOf[i] << '\n';
    }

    return 0;
}