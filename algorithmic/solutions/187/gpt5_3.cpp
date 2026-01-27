#include <bits/stdc++.h>
using namespace std;

const int MAXN = 512;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXN>> G(N);
    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        G[u].set(v);
        G[v].set(u);
    }

    bitset<MAXN> mask;
    for (int i = 0; i < N; ++i) mask.set(i);

    vector<bitset<MAXN>> H(N);
    vector<vector<int>> neH(N);
    vector<int> degH(N, 0);

    for (int u = 0; u < N; ++u) {
        H[u] = (~G[u]) & mask;
        H[u].reset(u);
        for (int v = 0; v < N; ++v) {
            if (H[u].test(v)) neH[u].push_back(v);
        }
        degH[u] = (int)neH[u].size();
    }

    // DSATUR coloring on H
    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    vector<bitset<MAXN>> usedColors(N); // colors used by H-neighbors

    int colored = 0, maxColor = 0;

    while (colored < N) {
        int best = -1;
        for (int i = 0; i < N; ++i) if (color[i] == 0) {
            if (best == -1 || sat[i] > sat[best] || (sat[i] == sat[best] && degH[i] > degH[best])) {
                best = i;
            }
        }
        int v = best;

        int c = 1;
        for (; c <= maxColor; ++c) {
            if (!usedColors[v].test(c)) break;
        }
        if (c == maxColor + 1) maxColor = c;
        color[v] = c;
        ++colored;

        for (int u : neH[v]) {
            if (color[u] == 0) {
                if (!usedColors[u].test(c)) {
                    usedColors[u].set(c);
                    ++sat[u];
                }
            }
        }
    }

    // Greedy improvement: try to move vertices to smaller color indices
    vector<bitset<MAXN>> colorBits(maxColor + 1);
    for (int v = 0; v < N; ++v) colorBits[color[v]].set(v);

    bool improved = true;
    int rounds = 0;
    while (improved && rounds < 2) {
        improved = false;
        ++rounds;

        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            if (color[a] != color[b]) return color[a] > color[b];
            if (degH[a] != degH[b]) return degH[a] > degH[b];
            return a < b;
        });

        for (int v : order) {
            int oldc = color[v];
            if (oldc == 1) continue;
            for (int c = 1; c < oldc; ++c) {
                if ((H[v] & colorBits[c]).none()) {
                    colorBits[oldc].reset(v);
                    colorBits[c].set(v);
                    color[v] = c;
                    improved = true;
                    break;
                }
            }
        }

        // Compress color indices to be consecutive
        vector<int> mapc(maxColor + 1, 0);
        int newMax = 0;
        for (int c = 1; c <= maxColor; ++c) {
            if (colorBits[c].any()) mapc[c] = ++newMax;
        }
        if (newMax < maxColor) {
            vector<bitset<MAXN>> newCB(newMax + 1);
            for (int c = 1; c <= maxColor; ++c) {
                int nc = mapc[c];
                if (nc) newCB[nc] |= colorBits[c];
            }
            colorBits.swap(newCB);
            for (int v = 0; v < N; ++v) color[v] = mapc[color[v]];
            maxColor = newMax;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << "\n";
    }

    return 0;
}