#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;
const int MAXC = 512;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> g(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N || u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) {
        sort(g[i].begin(), g[i].end());
        g[i].erase(unique(g[i].begin(), g[i].end()), g[i].end());
        deg[i] = (int)g[i].size();
    }

    using BSet = bitset<MAXC>;
    vector<BSet> neighColors(N);
    vector<int> satDeg(N, 0);
    vector<int> color(N, 0);

    int maxColor = 0;

    // DSatur algorithm
    for (int colored = 0; colored < N; ++colored) {
        int best = -1;
        int bestSat = -1;
        int bestDeg = -1;
        for (int i = 0; i < N; ++i) if (color[i] == 0) {
            if (satDeg[i] > bestSat || (satDeg[i] == bestSat && deg[i] > bestDeg)) {
                bestSat = satDeg[i];
                bestDeg = deg[i];
                best = i;
            }
        }
        int vtx = best;
        BSet &nc = neighColors[vtx];
        int c = 1;
        while (c < MAXC && nc.test(c)) ++c;
        if (c >= MAXC) c = 1; // fallback, should not occur
        color[vtx] = c;
        if (c > maxColor) maxColor = c;

        for (int u : g[vtx]) {
            if (color[u] == 0) {
                if (!neighColors[u].test(c)) {
                    neighColors[u].set(c);
                    satDeg[u]++;
                }
            }
        }
    }

    // Local improvement: greedy recoloring
    int passes = 10;
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    for (int it = 0; it < passes; ++it) {
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (color[a] != color[b]) return color[a] > color[b];
            return deg[a] > deg[b];
        });

        bool changed = false;
        int curMaxColor = maxColor;
        static unsigned char forbidden[MAXN + 2];

        for (int idx = 0; idx < N; ++idx) {
            int vtx = order[idx];
            int c = color[vtx];
            if (c <= 1) continue;

            memset(forbidden, 0, (curMaxColor + 1) * sizeof(unsigned char));
            for (int u : g[vtx]) {
                int cu = color[u];
                if (cu >= 1 && cu <= curMaxColor) forbidden[cu] = 1;
            }

            for (int newC = 1; newC < c; ++newC) {
                if (!forbidden[newC]) {
                    color[vtx] = newC;
                    changed = true;
                    break;
                }
            }
        }

        if (!changed) break;
        int newMax = 0;
        for (int i = 0; i < N; ++i)
            if (color[i] > newMax) newMax = color[i];
        maxColor = newMax;
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }

    return 0;
}