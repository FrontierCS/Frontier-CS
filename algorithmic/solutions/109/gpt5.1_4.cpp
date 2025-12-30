#include <bits/stdc++.h>
using namespace std;

uint64_t rng_state;

inline uint32_t rng() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    rng_state ^= rng_state << 8;
    return (uint32_t)rng_state;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int rs, cs;
    cin >> rs >> cs;
    rs--; cs--;

    int total = N * N;

    // Initialize RNG
    rng_state = (uint64_t)chrono::steady_clock::now().time_since_epoch().count()
                ^ (uint64_t)(uintptr_t)&N;

    // Precompute neighbors
    const int dr[8] = {2,1,-1,-2,-2,-1,1,2};
    const int dc[8] = {1,2,2,1,-1,-2,-2,-1};

    vector<array<int,8>> neigh(total);
    vector<unsigned char> neighCnt(total);

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int id = r * N + c;
            unsigned char cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    neigh[id][cnt++] = nr * N + nc;
                }
            }
            neighCnt[id] = cnt;
        }
    }

    vector<unsigned char> degBase(total), deg(total);
    for (int i = 0; i < total; ++i) {
        degBase[i] = neighCnt[i];
    }

    vector<unsigned char> visited(total);
    vector<int> path(total);
    vector<int> bestPath;
    bestPath.reserve(total);
    int bestLen = 0;

    long long approx = 150000000LL / (12LL * total); // heuristic operation budget
    if (approx < 1) approx = 1;
    if (approx > 2000) approx = 2000;
    int maxTries = (int)approx;

    int startId = rs * N + cs;

    for (int attempt = 0; attempt < maxTries; ++attempt) {
        // randomness probability increases with attempts, up to 40%
        int randomProb = (int)( (long long)(attempt) * 40 / maxTries );

        fill(visited.begin(), visited.end(), 0);
        deg = degBase;

        int len = 1;
        int cur = startId;
        visited[cur] = 1;
        path[0] = cur;

        unsigned char cntCur = neighCnt[cur];
        for (int i = 0; i < cntCur; ++i) {
            int u = neigh[cur][i];
            if (deg[u] > 0) --deg[u];
        }

        while (true) {
            int cand[8];
            int candCount = 0;
            unsigned char nc = neighCnt[cur];
            for (int i = 0; i < nc; ++i) {
                int v = neigh[cur][i];
                if (!visited[v]) {
                    cand[candCount++] = v;
                }
            }
            if (candCount == 0) break;

            int next;
            if (randomProb > 0 && (rng() % 100 < (uint32_t)randomProb)) {
                // Random choice among available moves
                next = cand[rng() % candCount];
            } else {
                // Warnsdorff: minimal degree heuristic with random tie-breaking
                int bestIdx = -1;
                int minDeg = 9;
                int sameCount = 0;
                for (int i = 0; i < candCount; ++i) {
                    int v = cand[i];
                    int dv = deg[v];
                    if (dv < minDeg) {
                        minDeg = dv;
                        bestIdx = i;
                        sameCount = 1;
                    } else if (dv == minDeg) {
                        ++sameCount;
                        if (rng() % sameCount == 0u) {
                            bestIdx = i;
                        }
                    }
                }
                next = cand[bestIdx];
            }

            cur = next;
            visited[cur] = 1;
            path[len++] = cur;

            unsigned char cntN = neighCnt[cur];
            for (int i = 0; i < cntN; ++i) {
                int u = neigh[cur][i];
                if (deg[u] > 0) --deg[u];
            }

            if (len == total) break;
        }

        if (len > bestLen) {
            bestLen = len;
            bestPath.assign(path.begin(), path.begin() + len);
        }

        if (bestLen == total) break;
    }

    // Output best found path
    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        int id = bestPath[i];
        int r = id / N;
        int c = id % N;
        cout << (r + 1) << ' ' << (c + 1) << '\n';
    }

    return 0;
}