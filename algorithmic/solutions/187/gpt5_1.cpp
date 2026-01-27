#include <bits/stdc++.h>
using namespace std;

static inline bool testColor(const vector<unsigned long long>& bs, int c) {
    int pos = c - 1;
    int idx = pos >> 6;
    int off = pos & 63;
    return (bs[idx] >> off) & 1ULL;
}

static inline bool setColor(vector<unsigned long long>& bs, int c) {
    int pos = c - 1;
    int idx = pos >> 6;
    int off = pos & 63;
    unsigned long long mask = 1ULL << off;
    bool already = (bs[idx] & mask) != 0ULL;
    bs[idx] |= mask;
    return !already;
}

vector<int> dsaturColoring(int N, const vector<vector<int>>& compAdj) {
    vector<int> color(N, 0);
    vector<int> degComp(N);
    for (int i = 0; i < N; ++i) degComp[i] = (int)compAdj[i].size();

    int W = (N + 63) / 64;
    vector<vector<unsigned long long>> sat(N, vector<unsigned long long>(W, 0ULL));
    vector<int> satCount(N, 0);

    int K = 0;

    for (int it = 0; it < N; ++it) {
        int best = -1;
        for (int v = 0; v < N; ++v) {
            if (color[v] != 0) continue;
            if (best == -1 ||
                satCount[v] > satCount[best] ||
                (satCount[v] == satCount[best] && degComp[v] > degComp[best]) ||
                (satCount[v] == satCount[best] && degComp[v] == degComp[best] && v < best)) {
                best = v;
            }
        }

        int chosenColor = 0;
        for (int c = 1; c <= K; ++c) {
            if (!testColor(sat[best], c)) {
                chosenColor = c;
                break;
            }
        }
        if (chosenColor == 0) {
            K++;
            chosenColor = K;
        }
        color[best] = chosenColor;

        for (int u : compAdj[best]) {
            if (color[u] == 0) {
                if (setColor(sat[u], chosenColor)) {
                    satCount[u]++;
                }
            }
        }
    }

    return color;
}

void greedyRecolor(vector<int>& color, const vector<vector<int>>& compAdj) {
    int N = (int)color.size();
    if (N == 0) return;

    bool changed = true;
    int maxPasses = 4; // small fixed number of passes
    while (changed && maxPasses--) {
        changed = false;
        int Kcur = 0;
        for (int v = 0; v < N; ++v) Kcur = max(Kcur, color[v]);
        if (Kcur <= 1) break;

        vector<vector<int>> byColor(Kcur + 1);
        for (int v = 0; v < N; ++v) {
            if (color[v] > 0) byColor[color[v]].push_back(v);
        }

        vector<int> stamp(Kcur + 1, 0);
        int curStamp = 0;

        for (int c = Kcur; c >= 1; --c) {
            for (int v : byColor[c]) {
                int oldc = color[v];
                if (oldc != c) continue; // might have changed earlier in this pass
                ++curStamp;
                for (int u : compAdj[v]) {
                    int cu = color[u];
                    if (cu > 0 && cu <= Kcur) stamp[cu] = curStamp;
                }
                for (int t = 1; t < oldc; ++t) {
                    if (stamp[t] != curStamp) {
                        color[v] = t;
                        changed = true;
                        break;
                    }
                }
            }
        }
    }
    // Final compression of color IDs to be contiguous
    int Kcur = 0;
    for (int v = 0; v < N; ++v) Kcur = max(Kcur, color[v]);
    vector<int> cnt(Kcur + 1, 0);
    for (int v = 0; v < N; ++v) if (color[v] > 0) cnt[color[v]]++;
    vector<int> mp(Kcur + 1, 0);
    int newK = 0;
    for (int c = 1; c <= Kcur; ++c) {
        if (cnt[c] > 0) mp[c] = ++newK;
    }
    for (int v = 0; v < N; ++v) if (color[v] > 0) color[v] = mp[color[v]];
}

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
        if (!adj[u][v]) {
            adj[u][v] = 1;
            adj[v][u] = 1;
        }
    }

    vector<vector<int>> compAdj(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (!adj[i][j]) {
                compAdj[i].push_back(j);
                compAdj[j].push_back(i);
            }
        }
    }

    vector<int> color = dsaturColoring(N, compAdj);
    greedyRecolor(color, compAdj);

    for (int i = 0; i < N; ++i) {
        if (color[i] <= 0) color[i] = 1; // safety, though DSATUR assigns all
        cout << color[i] << "\n";
    }

    return 0;
}