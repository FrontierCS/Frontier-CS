#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463393265ull) { if (!seed) seed = 88172645463393265ull; x = seed; }
    inline uint64_t next() { x ^= x << 7; x ^= x >> 9; return x; }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline uint32_t rand_range(uint32_t n) { return n ? (uint32_t)(next() % n) : 0; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<unsigned char> seen((size_t)N * (size_t)N, 0);
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        size_t idx1 = (size_t)u * (size_t)N + v;
        size_t idx2 = (size_t)v * (size_t)N + u;
        if (!seen[idx1]) {
            seen[idx1] = seen[idx2] = 1;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1900);

    XorShift64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int> bestColor(N, 1);
    int bestC = N + 1;

    // Buffers reused across iterations
    vector<int> color(N), sat(N);
    vector<unsigned char> used; // used[v*N + (c-1)] -> whether color c used by neighbor of v
    used.resize((size_t)N * (size_t)N);

    auto dsatur_once = [&](vector<int>& outColor)->int {
        // Init
        int maxColor = 0;
        int uncolored = N;
        fill(color.begin(), color.end(), 0);
        fill(sat.begin(), sat.end(), 0);
        memset(used.data(), 0, used.size());

        while (uncolored > 0) {
            // Select vertex with maximum saturation, tie by degree, then random.
            int bestU = -1;
            int bestSat = -1;
            int bestDeg = -1;
            int tieCount = 0;

            for (int v = 0; v < N; ++v) {
                if (color[v] != 0) continue;
                int s = sat[v];
                if (s > bestSat) {
                    bestSat = s;
                    bestDeg = deg[v];
                    bestU = v;
                    tieCount = 1;
                } else if (s == bestSat) {
                    if (deg[v] > bestDeg) {
                        bestDeg = deg[v];
                        bestU = v;
                        tieCount = 1;
                    } else if (deg[v] == bestDeg) {
                        // Reservoir sampling among ties
                        ++tieCount;
                        if (rng.rand_range((uint32_t)tieCount) == 0) {
                            bestU = v;
                        }
                    }
                }
            }

            // Assign smallest available color
            int chosen = 1;
            size_t base = (size_t)bestU * (size_t)N;
            for (; chosen <= maxColor; ++chosen) {
                if (!used[base + (size_t)(chosen - 1)]) break;
            }
            if (chosen > maxColor) maxColor = chosen;
            color[bestU] = chosen;
            --uncolored;

            // Update neighbors
            for (int w : adj[bestU]) {
                if (color[w] != 0) continue;
                size_t idx = (size_t)w * (size_t)N + (size_t)(chosen - 1);
                if (!used[idx]) {
                    used[idx] = 1;
                    ++sat[w];
                }
            }
        }
        outColor = color;
        return maxColor;
    };

    // First run deterministic-ish DSATUR
    {
        vector<int> curColor(N);
        int c = dsatur_once(curColor);
        if (c < bestC) {
            bestC = c;
            bestColor = curColor;
        }
    }

    // Multiple randomized restarts within time
    while (chrono::steady_clock::now() < deadline) {
        vector<int> curColor(N);
        int c = dsatur_once(curColor);
        if (c < bestC) {
            bestC = c;
            bestColor = curColor;
            // If best is very small, still continue until time
        }
    }

    // Output best coloring found
    for (int i = 0; i < N; ++i) {
        cout << bestColor[i] << '\n';
    }
    return 0;
}