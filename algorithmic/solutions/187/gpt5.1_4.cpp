#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;
const int MAXC = 500;

static bool adj[MAXN][MAXN];
vector<int> compAdj[MAXN];
bitset<MAXC + 1> usedColors[MAXN];
int colorArr[MAXN];
int saturationArr[MAXN];
int degreeComp[MAXN];
bool isColored[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    memset(adj, 0, sizeof(adj));
    for (int i = 0; i < N; ++i) {
        compAdj[i].clear();
    }

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!adj[u][v]) {
            adj[u][v] = adj[v][u] = true;
        }
    }

    // Build complement adjacency list
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!adj[i][j]) {
                compAdj[i].push_back(j);
                compAdj[j].push_back(i);
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        degreeComp[i] = (int)compAdj[i].size();
        colorArr[i] = 0;
        saturationArr[i] = 0;
        isColored[i] = false;
        usedColors[i].reset();
    }

    int K = 0;
    int coloredCnt = 0;

    // DSatur on complement graph
    while (coloredCnt < N) {
        int v = -1;
        int bestSat = -1;
        int bestDeg = -1;
        for (int i = 0; i < N; ++i) {
            if (isColored[i]) continue;
            int sat = saturationArr[i];
            int deg = degreeComp[i];
            if (sat > bestSat || (sat == bestSat && deg > bestDeg)) {
                bestSat = sat;
                bestDeg = deg;
                v = i;
            }
        }

        int c = 1;
        while (c <= K && usedColors[v].test(c)) ++c;
        if (c > K) K = c;
        colorArr[v] = c;
        isColored[v] = true;
        ++coloredCnt;

        for (int u : compAdj[v]) {
            if (isColored[u]) continue;
            if (!usedColors[u].test(c)) {
                usedColors[u].set(c);
                ++saturationArr[u];
            }
        }
    }

    // Merge color classes when their union is still a clique in original graph
    vector<vector<int>> classes(K + 1);
    for (int v = 0; v < N; ++v) {
        int c = colorArr[v];
        if (c >= 1 && c <= K) {
            classes[c].push_back(v);
        }
    }

    for (int i = 1; i <= K; ++i) {
        if (classes[i].empty()) continue;
        for (int j = i + 1; j <= K; ++j) {
            if (classes[j].empty()) continue;

            bool ok = true;
            for (int u : classes[i]) {
                for (int v : classes[j]) {
                    if (!adj[u][v]) {
                        ok = false;
                        break;
                    }
                }
                if (!ok) break;
            }

            if (ok) {
                // Merge class j into class i
                for (int v : classes[j]) {
                    colorArr[v] = i;
                    classes[i].push_back(v);
                }
                classes[j].clear();
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << colorArr[i] << '\n';
    }

    return 0;
}