#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    r0--; c0--;
    const int total = N * N;
    const int start = r0 * N + c0;

    // Precompute neighbors
    const int drs[8] = {-2,-2,-1,-1,1,1,2,2};
    const int dcs[8] = {-1,1,-2,2,-2,2,-1,1};
    vector<array<int,8>> neigh(total);
    vector<uint8_t> ncnt(total, 0);
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int id = r * N + c;
            uint8_t cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + drs[k];
                int nc = c + dcs[k];
                if (0 <= nr && nr < N && 0 <= nc && nc < N) {
                    neigh[id][cnt++] = nr * N + nc;
                }
            }
            ncnt[id] = cnt;
            for (int k = cnt; k < 8; ++k) neigh[id][k] = -1;
        }
    }

    vector<uint8_t> baseDeg = ncnt;
    vector<int> bestPath;
    bestPath.reserve(total);
    int bestLen = 0;

    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 0.95; // seconds, soft limit inside 1s

    auto attempt = [&](uint64_t seed) -> int {
        vector<uint8_t> degRem = baseDeg;
        vector<unsigned char> vis(total, 0);
        vector<int> path;
        path.reserve(total);

        int cur = start;
        vis[cur] = 1;
        path.push_back(cur);
        // decrease degree of neighbors
        uint8_t cntc = ncnt[cur];
        for (int i = 0; i < cntc; ++i) {
            int w = neigh[cur][i];
            if (!vis[w]) degRem[w]--;
        }

        while ((int)path.size() < total) {
            int best = -1;
            int bestHV = 100;
            int bestMin2 = 100;
            uint64_t bestRand = 0;

            bool hasCandidate = false;
            bool hasNonZero = false;

            uint8_t cnt = ncnt[cur];
            for (int i = 0; i < cnt; ++i) {
                int v = neigh[cur][i];
                if (!vis[v]) {
                    hasCandidate = true;
                    if (degRem[v] > 0) hasNonZero = true;
                }
            }
            if (!hasCandidate) break;

            bool preferNonZero = hasNonZero && ((int)path.size() + 1 < total);

            // First pass (prefer non-zero deg if available)
            for (int i = 0; i < cnt; ++i) {
                int v = neigh[cur][i];
                if (v < 0 || vis[v]) continue;
                int hv = degRem[v];
                if (preferNonZero && hv == 0) continue;

                int min2 = 9;
                uint8_t cntv = ncnt[v];
                for (int j = 0; j < cntv; ++j) {
                    int w = neigh[v][j];
                    if (w >= 0 && !vis[w]) {
                        int dw = degRem[w];
                        if (dw < min2) min2 = dw;
                    }
                }
                uint64_t rkey = splitmix64((uint64_t)v ^ (seed + path.size() * 0x9e3779b97f4a7c15ULL));
                if (best == -1 || hv < bestHV || (hv == bestHV && (min2 < bestMin2 || (min2 == bestMin2 && rkey < bestRand)))) {
                    best = v;
                    bestHV = hv;
                    bestMin2 = min2;
                    bestRand = rkey;
                }
            }

            // If nothing selected (all candidates had hv=0 but we preferred nonzero), allow hv=0
            if (best == -1) {
                for (int i = 0; i < cnt; ++i) {
                    int v = neigh[cur][i];
                    if (v < 0 || vis[v]) continue;
                    int hv = degRem[v];
                    int min2 = 9;
                    uint8_t cntv = ncnt[v];
                    for (int j = 0; j < cntv; ++j) {
                        int w = neigh[v][j];
                        if (w >= 0 && !vis[w]) {
                            int dw = degRem[w];
                            if (dw < min2) min2 = dw;
                        }
                    }
                    uint64_t rkey = splitmix64((uint64_t)v ^ (seed + path.size() * 0x9e3779b97f4a7c15ULL));
                    if (best == -1 || hv < bestHV || (hv == bestHV && (min2 < bestMin2 || (min2 == bestMin2 && rkey < bestRand)))) {
                        best = v;
                        bestHV = hv;
                        bestMin2 = min2;
                        bestRand = rkey;
                    }
                }
            }

            if (best == -1) break;
            int v = best;
            vis[v] = 1;
            path.push_back(v);
            // update degrees
            uint8_t cntv = ncnt[v];
            for (int i = 0; i < cntv; ++i) {
                int w = neigh[v][i];
                if (!vis[w]) degRem[w]--;
            }
            cur = v;
        }
        if ((int)path.size() > bestLen) {
            bestLen = (int)path.size();
            bestPath = path;
        }
        return (int)path.size();
    };

    // First, a deterministic attempt
    attempt(0x123456789abcdef0ULL);
    if (bestLen == total) {
        cout << bestLen << '\n';
        for (int id : bestPath) {
            int rr = id / N;
            int cc = id % N;
            cout << rr + 1 << ' ' << cc + 1 << '\n';
        }
        return 0;
    }

    // Randomized attempts until time runs out or success
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()
                        ^ splitmix64((uint64_t)start) ^ splitmix64((uint64_t)N));
    int attempts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > TIME_LIMIT) break;
        uint64_t seed = rng();
        attempt(seed);
        attempts++;
        if (bestLen == total) break;
    }

    cout << bestLen << '\n';
    for (int id : bestPath) {
        int rr = id / N;
        int cc = id % N;
        cout << rr + 1 << ' ' << cc + 1 << '\n';
    }
    return 0;
}