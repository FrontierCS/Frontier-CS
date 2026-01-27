#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed=88172645463393265ull) : x(seed) {}
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    int64_t NB = 1LL * N * N;

    // Precompute neighbors
    const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
    const int dc[8] = {-1,1,-2,2,-2,2,-1,1};
    vector<unsigned char> nbCnt(NB, 0);
    vector<int> nb(8 * NB, -1);

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int id = r * N + c;
            unsigned char k = 0;
            for (int m = 0; m < 8; ++m) {
                int nr = r + dr[m], nc = c + dc[m];
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    nb[id*8 + k] = nr * N + nc;
                    ++k;
                }
            }
            nbCnt[id] = k;
        }
    }

    vector<unsigned char> deg0(NB);
    for (int64_t i = 0; i < NB; ++i) deg0[i] = nbCnt[i];

    auto attempt = [&](int start_r, int start_c, uint64_t seed)->vector<int> {
        RNG rng(seed);
        vector<unsigned char> visited(NB, 0);
        vector<unsigned char> deg(NB);
        memcpy(deg.data(), deg0.data(), NB * sizeof(unsigned char));
        vector<int> path;
        path.reserve(NB);

        int start = start_r * N + start_c;
        visited[start] = 1;
        path.push_back(start);
        // update degrees of neighbors of start
        for (int i = 0; i < nbCnt[start]; ++i) {
            int w = nb[start*8 + i];
            if (!visited[w]) {
                if (deg[w] > 0) --deg[w];
            }
        }

        int cur = start;
        for (int64_t step = 1; step < NB; ++step) {
            int best = -1;
            int bestDeg = 100;
            int bestSecond = 100;
            bool foundPositive = false;
            uint64_t bestRand = 0;

            // Precompute candidate selection
            for (int i = 0; i < nbCnt[cur]; ++i) {
                int v = nb[cur*8 + i];
                if (visited[v]) continue;
                int d = deg[v];
                int second = 100;
                // prefer positive degree if possible
                if (d > 0) {
                    // compute min next-degree among v's neighbors (lookahead)
                    for (int j = 0; j < nbCnt[v]; ++j) {
                        int w = nb[v*8 + j];
                        if (!visited[w]) {
                            int dw = deg[w];
                            if (dw < second) second = dw;
                        }
                    }
                    if (!foundPositive) {
                        // first positive candidate
                        best = v; bestDeg = d; bestSecond = second; foundPositive = true; bestRand = rng.next();
                    } else {
                        if (d < bestDeg) {
                            best = v; bestDeg = d; bestSecond = second; bestRand = rng.next();
                        } else if (d == bestDeg) {
                            if (second < bestSecond) {
                                best = v; bestSecond = second; bestRand = rng.next();
                            } else if (second == bestSecond) {
                                uint64_t rr = rng.next();
                                if (rr < bestRand) { best = v; bestRand = rr; }
                            }
                        }
                    }
                } else if (!foundPositive) {
                    // consider zero-degree candidates only if no positive exists
                    // For zero-degree, second is irrelevant; use random tie-break to avoid bias
                    if (best == -1) {
                        best = v; bestDeg = d; bestSecond = second; bestRand = rng.next();
                    } else {
                        uint64_t rr = rng.next();
                        if (rr < bestRand) { best = v; bestRand = rr; }
                    }
                }
            }

            if (best == -1) {
                // dead end
                return path;
            }

            int nxt = best;
            visited[nxt] = 1;
            path.push_back(nxt);
            // update degrees of neighbors of nxt
            for (int i = 0; i < nbCnt[nxt]; ++i) {
                int w = nb[nxt*8 + i];
                if (!visited[w]) {
                    if (deg[w] > 0) --deg[w];
                }
            }
            cur = nxt;
        }
        return path;
    };

    vector<int> bestPath;
    int64_t bestLen = 0;

    auto tstart = chrono::steady_clock::now();
    uint64_t seedBase = ((uint64_t)N << 48) ^ ((uint64_t)(r0+1) << 24) ^ (uint64_t)(c0+1) ^ 0x9e3779b97f4a7c15ull;

    int maxTries = 1000000000; // we will limit by time
    for (int attemptId = 0; attemptId < maxTries; ++attemptId) {
        uint64_t seed = seedBase + (uint64_t)attemptId * 0x9e3779b97f4a7c15ull;
        vector<int> path = attempt(r0, c0, seed);
        if ((int64_t)path.size() > bestLen) {
            bestLen = (int64_t)path.size();
            bestPath.swap(path);
            if (bestLen == NB) break;
        }
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - tstart).count();
        if (elapsed > 0.95) break;
    }

    // Output
    cout << bestLen << '\n';
    for (int64_t i = 0; i < bestLen; ++i) {
        int id = bestPath[i];
        int rr = id / N;
        int cc = id % N;
        cout << (rr + 1) << ' ' << (cc + 1);
        if (i + 1 < bestLen) cout << '\n';
    }
    return 0;
}