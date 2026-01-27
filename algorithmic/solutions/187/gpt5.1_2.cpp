#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;
using Bitset = bitset<MAXN + 1>;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<Bitset> adj(N + 1), comp(N + 1);

    for (int e = 0; e < M; ++e) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > N || v < 1 || v > N) continue;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    // Build complement graph
    for (int i = 1; i <= N; ++i) {
        comp[i] = ~adj[i];
        comp[i].reset(0);
        comp[i].reset(i);
    }

    // DSATUR coloring on complement graph
    vector<int> color(N + 1, 0);
    vector<int> sat_deg(N + 1, 0);
    vector<int> degC(N + 1, 0);
    vector<Bitset> neighColor(N + 1);

    for (int i = 1; i <= N; ++i) {
        degC[i] = (int)comp[i].count();
    }

    Bitset uncolored;
    for (int i = 1; i <= N; ++i) uncolored.set(i);

    int maxColor = 0;

    while (uncolored.any()) {
        int v = -1;
        int bestSat = -1;
        int bestDeg = -1;

        for (int i = 1; i <= N; ++i) {
            if (!uncolored.test(i)) continue;
            if (sat_deg[i] > bestSat || (sat_deg[i] == bestSat && degC[i] > bestDeg)) {
                bestSat = sat_deg[i];
                bestDeg = degC[i];
                v = i;
            }
        }

        if (v == -1) break;  // safety

        int c;
        for (c = 1; c <= maxColor; ++c) {
            if (!neighColor[v].test(c)) break;
        }
        if (c == maxColor + 1) ++maxColor;
        color[v] = c;
        uncolored.reset(v);

        for (int u = 1; u <= N; ++u) {
            if (!uncolored.test(u)) continue;
            if (!comp[v].test(u)) continue;
            if (!neighColor[u].test(c)) {
                neighColor[u].set(c);
                ++sat_deg[u];
            }
        }
    }

    if (maxColor == 0) {
        maxColor = 1;
        for (int i = 1; i <= N; ++i) color[i] = 1;
    } else {
        for (int i = 1; i <= N; ++i) {
            if (color[i] == 0) color[i] = 1; // fallback safety
        }
    }

    // Local improvement: try to move vertices to existing colors to reduce number of cliques
    vector<Bitset> colorSets(maxColor + 1);
    for (int c = 1; c <= maxColor; ++c) colorSets[c].reset();
    for (int v = 1; v <= N; ++v) {
        colorSets[color[v]].set(v);
    }

    const int MAX_ITER = 5;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        bool changed = false;
        for (int v = 1; v <= N; ++v) {
            int oldColor = color[v];
            Bitset notNeigh = ~adj[v];

            colorSets[oldColor].reset(v);

            int bestColor = oldColor;
            for (int c = 1; c <= maxColor; ++c) {
                if (c == oldColor) continue;
                if (!colorSets[c].any()) continue;
                Bitset conflict = colorSets[c] & notNeigh;
                if (conflict.any()) continue;
                bestColor = c;
                break;
            }

            if (bestColor != oldColor) {
                color[v] = bestColor;
                colorSets[bestColor].set(v);
                changed = true;
            } else {
                colorSets[oldColor].set(v);
            }
        }
        if (!changed) break;
    }

    // Compress color ids to be consecutive from 1
    vector<int> mapColor(maxColor + 1, 0);
    int newColorCount = 0;
    for (int c = 1; c <= maxColor; ++c) {
        if (colorSets[c].any()) {
            mapColor[c] = ++newColorCount;
        }
    }
    for (int v = 1; v <= N; ++v) {
        int nc = mapColor[color[v]];
        color[v] = (nc == 0 ? 1 : nc); // safety
    }

    for (int i = 1; i <= N; ++i) {
        cout << color[i] << "\n";
    }

    return 0;
}