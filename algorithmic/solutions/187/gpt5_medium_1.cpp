#include <bits/stdc++.h>
using namespace std;

static inline int popcountll(unsigned long long x){ return __builtin_popcountll(x); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int W = (N + 63) >> 6; // number of 64-bit blocks

    auto make_maskN = [&](int N)->unsigned long long {
        int r = N % 64;
        if (r == 0) return ~0ULL;
        return (1ULL << r) - 1ULL;
    };
    unsigned long long lastBlockMask = make_maskN(N);

    // Complement adjacency: comp[u][block] has 1 if edge exists in complement between u and v
    vector<vector<unsigned long long>> comp(N, vector<unsigned long long>(W, ~0ULL));
    for (int i = 0; i < N; ++i) {
        if (W > 0) comp[i][W-1] &= lastBlockMask; // mask off bits beyond N
        // clear self-loop
        comp[i][i >> 6] &= ~(1ULL << (i & 63));
    }
    auto clearEdgeComp = [&](int u, int v){
        comp[u][v >> 6] &= ~(1ULL << (v & 63));
        comp[v][u >> 6] &= ~(1ULL << (u & 63));
    };

    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v || u < 0 || v < 0 || u >= N || v >= N) continue;
        clearEdgeComp(u, v); // remove edge from complement for original edges
    }

    // Degrees in complement
    vector<int> degComp(N, 0);
    for (int i = 0; i < N; ++i) {
        int d = 0;
        for (int b = 0; b < W; ++b) d += popcountll(comp[i][b]);
        degComp[i] = d;
    }

    // DSATUR coloring on complement
    vector<int> color(N, 0);
    vector<int> satdeg(N, 0);
    vector<vector<unsigned long long>> usedColors(N, vector<unsigned long long>(W, 0)); // up to N colors
    auto getBit = [&](const vector<unsigned long long>& a, int pos)->bool {
        return (a[pos >> 6] >> (pos & 63)) & 1ULL;
    };
    auto setBitIfUnset = [&](vector<unsigned long long>& a, int pos)->bool {
        unsigned long long m = 1ULL << (pos & 63);
        int idx = pos >> 6;
        if (a[idx] & m) return false;
        a[idx] |= m;
        return true;
    };

    int K = 0;
    for (int it = 0; it < N; ++it) {
        int best = -1, bestSat = -1, bestDeg = -1;
        for (int i = 0; i < N; ++i) if (color[i] == 0) {
            int s = satdeg[i];
            if (s > bestSat || (s == bestSat && degComp[i] > bestDeg)) {
                best = i; bestSat = s; bestDeg = degComp[i];
            }
        }
        int chosen = 0;
        for (int c = 1; c <= K; ++c) {
            if (!getBit(usedColors[best], c - 1)) {
                chosen = c; break;
            }
        }
        if (chosen == 0) { K++; chosen = K; }
        color[best] = chosen;

        // Update saturation of uncolored neighbors
        for (int b = 0; b < W; ++b) {
            unsigned long long mask = comp[best][b];
            while (mask) {
                unsigned long long t = mask & -mask;
                int r = __builtin_ctzll(mask);
                int nb = (b << 6) + r;
                if (nb < N && color[nb] == 0) {
                    if (setBitIfUnset(usedColors[nb], chosen - 1)) {
                        satdeg[nb]++;
                    }
                }
                mask ^= t;
            }
        }
    }

    // Improvement: greedy moves to lower color indices if possible
    auto hasAnyBits = [&](const vector<unsigned long long>& v) -> bool {
        for (auto x : v) if (x) return true;
        return false;
    };
    auto setBitV = [&](vector<unsigned long long>& a, int pos){ a[pos>>6] |= (1ULL << (pos & 63)); };
    auto clearBitV = [&](vector<unsigned long long>& a, int pos){ a[pos>>6] &= ~(1ULL << (pos & 63)); };

    vector<vector<unsigned long long>> colorMask(K + 1, vector<unsigned long long>(W, 0));
    for (int v = 0; v < N; ++v) setBitV(colorMask[color[v]], v);

    bool changed = true;
    while (changed) {
        changed = false;
        for (int v = 0; v < N; ++v) {
            int fromC = color[v];
            for (int c = 1; c < fromC; ++c) {
                bool conflict = false;
                for (int b = 0; b < W; ++b) {
                    if (comp[v][b] & colorMask[c][b]) { conflict = true; break; }
                }
                if (!conflict) {
                    clearBitV(colorMask[fromC], v);
                    setBitV(colorMask[c], v);
                    color[v] = c;
                    changed = true;
                    break;
                }
            }
        }
        // compress color ids to 1..K without gaps
        vector<int> mapC(K + 1, 0);
        int newK = 0;
        for (int c = 1; c <= K; ++c) {
            if (hasAnyBits(colorMask[c])) mapC[c] = ++newK;
        }
        if (newK < K) {
            vector<vector<unsigned long long>> newMask(newK + 1, vector<unsigned long long>(W, 0));
            for (int v = 0; v < N; ++v) {
                int nc = mapC[color[v]];
                color[v] = nc;
                setBitV(newMask[nc], v);
            }
            colorMask.swap(newMask);
            K = newK;
            changed = true;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}