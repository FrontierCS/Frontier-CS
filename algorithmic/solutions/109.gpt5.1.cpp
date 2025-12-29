#include <bits/stdc++.h>
using namespace std;

const int MAXN = 666;
const int MAXCELLS = MAXN * MAXN;

static uint8_t visitedArr[MAXCELLS];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int r0, c0;
    if (!(cin >> N)) return 0;
    cin >> r0 >> c0;
    --r0; --c0;

    int nCells = N * N;
    int startId = r0 * N + c0;

    // Precompute adjacency
    vector<array<int, 8>> adj(nCells);
    vector<uint8_t> adjLen(nCells, 0);

    const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
    const int dc[8] = {-1,1,-2,2,-2,2,-1,1};

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int id = r * N + c;
            uint8_t &len = adjLen[id];
            len = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    adj[id][len++] = nr * N + nc;
                }
            }
        }
    }

    // Timing and RNG
    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 0.5; // seconds for search (leave time for I/O)
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestPath;
    bestPath.reserve(nCells);
    int bestLen = 0;

    const int MAX_ATTEMPTS = 5000;

    for (int attempt = 0; attempt < MAX_ATTEMPTS; ++attempt) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed >= TIME_LIMIT) break;

        memset(visitedArr, 0, nCells * sizeof(uint8_t));

        vector<int> path;
        path.reserve(nCells);

        int cur = startId;
        visitedArr[cur] = 1;
        path.push_back(cur);

        while (true) {
            uint8_t bestDeg = 9;
            int cand[8];
            int candCount = 0;

            uint8_t curAdjLen = adjLen[cur];
            for (int i = 0; i < curAdjLen; ++i) {
                int nx = adj[cur][i];
                if (visitedArr[nx]) continue;

                uint8_t nxAdjLen = adjLen[nx];
                uint8_t deg = 0;
                for (int j = 0; j < nxAdjLen; ++j) {
                    int ny = adj[nx][j];
                    if (!visitedArr[ny]) ++deg;
                }

                if (deg < bestDeg) {
                    bestDeg = deg;
                    candCount = 0;
                    cand[candCount++] = nx;
                } else if (deg == bestDeg) {
                    cand[candCount++] = nx;
                }
            }

            if (candCount == 0) break;

            int chosen;
            if (candCount == 1) {
                chosen = cand[0];
            } else {
                chosen = cand[rng() % candCount];
            }

            visitedArr[chosen] = 1;
            path.push_back(chosen);
            cur = chosen;

            if ((int)path.size() == nCells) break;
        }

        if ((int)path.size() > bestLen) {
            bestLen = (int)path.size();
            bestPath.swap(path);
            if (bestLen == nCells) break;
        }
    }

    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        int id = bestPath[i];
        int r = id / N + 1;
        int c = id % N + 1;
        cout << r << ' ' << c << '\n';
    }

    return 0;
}