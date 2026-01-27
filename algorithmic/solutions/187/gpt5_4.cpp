#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    int W = (N + 63) / 64;

    vector<vector<uint64_t>> adjOrig(N, vector<uint64_t>(W, 0));
    for (int i = 0; i < M; ++i) {
        int u, v; 
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adjOrig[u][v >> 6] |= (1ULL << (v & 63));
        adjOrig[v][u >> 6] |= (1ULL << (u & 63));
    }

    vector<uint64_t> maskWords(W, ~0ULL);
    for (int w = 0; w < W; ++w) {
        int rem = N - (w << 6);
        if (rem >= 64) maskWords[w] = ~0ULL;
        else if (rem <= 0) maskWords[w] = 0ULL;
        else maskWords[w] = (1ULL << rem) - 1;
    }

    vector<vector<uint64_t>> adjComp(N, vector<uint64_t>(W, 0));
    for (int u = 0; u < N; ++u) {
        for (int w = 0; w < W; ++w) {
            adjComp[u][w] = (~adjOrig[u][w]) & maskWords[w];
        }
        int ww = u >> 6, bb = u & 63;
        adjComp[u][ww] &= ~(1ULL << bb);
    }

    vector<int> degComp(N, 0);
    for (int u = 0; u < N; ++u) {
        int sum = 0;
        for (int w = 0; w < W; ++w) sum += __builtin_popcountll(adjComp[u][w]);
        degComp[u] = sum;
    }

    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    int Wcol = (N + 63) / 64;
    vector<vector<uint64_t>> colorMask(N, vector<uint64_t>(Wcol, 0));
    vector<char> uncolored(N, 1);

    auto getbit = [&](const vector<uint64_t>& mask, int c)->bool {
        int idx = (c - 1) >> 6;
        int pos = (c - 1) & 63;
        return (mask[idx] >> pos) & 1ULL;
    };
    auto setbit = [&](vector<uint64_t>& mask, int c) {
        int idx = (c - 1) >> 6;
        int pos = (c - 1) & 63;
        mask[idx] |= (1ULL << pos);
    };

    int numColors = 0;
    for (int it = 0; it < N; ++it) {
        int best = -1, bestSat = -1, bestDeg = -1;
        for (int v = 0; v < N; ++v) if (uncolored[v]) {
            if (sat[v] > bestSat || (sat[v] == bestSat && degComp[v] > bestDeg) || (sat[v] == bestSat && degComp[v] == bestDeg && (best == -1 || v < best))) {
                best = v;
                bestSat = sat[v];
                bestDeg = degComp[v];
            }
        }
        int u = best;
        if (u == -1) break;

        int assign = 0;
        for (int c = 1; c <= numColors; ++c) {
            if (!getbit(colorMask[u], c)) { assign = c; break; }
        }
        if (!assign) assign = ++numColors;

        color[u] = assign;
        uncolored[u] = 0;

        for (int w = 0; w < W; ++w) {
            uint64_t bits = adjComp[u][w];
            while (bits) {
                uint64_t t = bits & -bits;
                int b = __builtin_ctzll(bits);
                int v = (w << 6) + b;
                if (v < N && uncolored[v]) {
                    if (!getbit(colorMask[v], assign)) {
                        setbit(colorMask[v], assign);
                        sat[v]++;
                    }
                }
                bits ^= t;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}