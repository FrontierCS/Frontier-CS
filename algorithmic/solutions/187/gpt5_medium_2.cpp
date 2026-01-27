#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<unsigned char> adj(N * N, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u * N + v] = 1;
        adj[v * N + u] = 1;
    }
    // Build complement graph
    vector<vector<int>> compAdj(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!adj[i * N + j]) {
                compAdj[i].push_back(j);
                compAdj[j].push_back(i);
            }
        }
    }
    vector<int> degComp(N);
    for (int i = 0; i < N; ++i) degComp[i] = (int)compAdj[i].size();

    // DSATUR on complement graph
    int L = (N + 63) >> 6; // blocks for colors bitset
    vector<uint64_t> usedColorsBits((size_t)N * L, 0ULL); // for uncolored vertices
    auto getbit = [&](int v, int c)->bool {
        int x = c - 1;
        return (usedColorsBits[(size_t)v * L + (x >> 6)] >> (x & 63)) & 1ULL;
    };
    auto setbit = [&](int v, int c) {
        int x = c - 1;
        usedColorsBits[(size_t)v * L + (x >> 6)] |= (1ULL << (x & 63));
    };

    vector<int> color(N, 0), sat(N, 0);
    int maxColor = 0;
    for (int step = 0; step < N; ++step) {
        int v = -1, bestSat = -1, bestDeg = -1, bestIdx = -1;
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            if (sat[i] > bestSat || (sat[i] == bestSat && (degComp[i] > bestDeg || (degComp[i] == bestDeg && i < bestIdx)))) {
                bestSat = sat[i];
                bestDeg = degComp[i];
                bestIdx = i;
                v = i;
            }
        }
        int chosen = 0;
        for (int c = 1; c <= maxColor; ++c) {
            if (!getbit(v, c)) { chosen = c; break; }
        }
        if (chosen == 0) chosen = ++maxColor;
        color[v] = chosen;
        for (int u : compAdj[v]) {
            if (color[u] == 0) {
                if (!getbit(u, chosen)) {
                    setbit(u, chosen);
                    sat[u]++;
                }
            }
        }
    }

    // Improvement: try to reduce number of colors by moving vertices to lower colors
    vector<vector<int>> classes(maxColor + 1);
    for (int i = 0; i < N; ++i) classes[color[i]].push_back(i);

    bool changed = true;
    while (changed) {
        changed = false;
        for (int c = maxColor; c >= 2; --c) {
            if (classes[c].empty()) continue;
            int idx = 0;
            while (idx < (int)classes[c].size()) {
                int v = classes[c][idx];
                bool moved = false;
                for (int nc = 1; nc < c; ++nc) {
                    bool ok = true;
                    for (int u : compAdj[v]) {
                        if (color[u] == nc) { ok = false; break; }
                    }
                    if (ok) {
                        color[v] = nc;
                        classes[nc].push_back(v);
                        classes[c][idx] = classes[c].back();
                        classes[c].pop_back();
                        moved = true;
                        changed = true;
                        break;
                    }
                }
                if (!moved) ++idx;
            }
            if (c == maxColor && classes[c].empty()) {
                --maxColor;
                changed = true;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}