#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;
const int MAXW = (MAXN + 63) / 64;

uint64_t compAdj[MAXN][MAXW];
uint64_t adjG[MAXN][MAXW];
int degComp[MAXN];

int dsatur(int N, int W, uint64_t compAdj[][MAXW], const int degComp[], vector<int>& color, mt19937_64 &rng) {
    static bool colored[MAXN];
    static int satDeg[MAXN];
    static bitset<MAXN> neighColors[MAXN];

    for (int i = 0; i < N; ++i) {
        colored[i] = false;
        satDeg[i] = 0;
        neighColors[i].reset();
        color[i] = -1;
    }

    int remaining = N;
    int maxColor = 0;

    while (remaining > 0) {
        int bestSat = -1;
        int bestDeg = -1;
        vector<int> cand;
        cand.reserve(N);

        for (int v = 0; v < N; ++v) {
            if (colored[v]) continue;
            int s = satDeg[v];
            if (s > bestSat) {
                bestSat = s;
                bestDeg = degComp[v];
                cand.clear();
                cand.push_back(v);
            } else if (s == bestSat) {
                int dv = degComp[v];
                if (dv > bestDeg) {
                    bestDeg = dv;
                    cand.clear();
                    cand.push_back(v);
                } else if (dv == bestDeg) {
                    cand.push_back(v);
                }
            }
        }

        int v;
        if (cand.size() == 1) {
            v = cand[0];
        } else {
            uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
            v = cand[dist(rng)];
        }

        int c;
        for (c = 0; c < maxColor; ++c) {
            if (!neighColors[v].test(c)) break;
        }
        if (c == maxColor) maxColor++;

        color[v] = c;
        colored[v] = true;
        --remaining;

        for (int w = 0; w < W; ++w) {
            uint64_t mask = compAdj[v][w];
            while (mask) {
                uint64_t lsb = mask & -mask;
                int bit = __builtin_ctzll(mask);
                int u = w * 64 + bit;
                mask ^= lsb;
                if (u >= N) continue;
                if (!colored[u]) {
                    if (!neighColors[u].test(c)) {
                        neighColors[u].set(c);
                        ++satDeg[u];
                    }
                }
            }
        }
    }

    return maxColor;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int W = (N + 63) / 64;

    for (int i = 0; i < N; ++i)
        for (int w = 0; w < W; ++w)
            adjG[i][w] = 0;

    for (int e = 0; e < M; ++e) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adjG[u][v / 64] |= 1ULL << (v % 64);
        adjG[v][u / 64] |= 1ULL << (u % 64);
    }

    uint64_t wordFullMask[MAXW];
    for (int w = 0; w < W; ++w) {
        if (w == W - 1 && (N % 64) != 0) {
            wordFullMask[w] = (1ULL << (N % 64)) - 1;
        } else {
            wordFullMask[w] = ~0ULL;
        }
    }

    for (int i = 0; i < N; ++i) {
        adjG[i][i / 64] |= 1ULL << (i % 64);
        for (int w = 0; w < W; ++w) {
            compAdj[i][w] = (~adjG[i][w]) & wordFullMask[w];
        }
        compAdj[i][i / 64] &= ~(1ULL << (i % 64));

        int deg = 0;
        for (int w = 0; w < W; ++w) {
            deg += __builtin_popcountll(compAdj[i][w]);
        }
        degComp[i] = deg;
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestColor(N);
    int bestK = N;

    auto start = chrono::steady_clock::now();
    int iterations = 0;

    while (true) {
        vector<int> color(N);
        int K = dsatur(N, W, compAdj, degComp, color, rng);
        if (K < bestK) {
            bestK = K;
            bestColor = color;
        }
        ++iterations;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > 1.8 || iterations >= 1000) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestColor[i] + 1) << '\n';
    }

    return 0;
}