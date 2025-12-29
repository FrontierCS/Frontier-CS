#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0; // to 0-based

    int total = N * N;

    vector<int> dr{2, 1, -1, -2, -2, -1, 1, 2};
    vector<int> dc{1, 2,  2,  1, -1, -2,-2,-1};

    vector<char> visited(N * N, 0);
    vector<pair<int,int>> path;
    path.reserve(total);
    vector<pair<int,int>> bestPath;
    bestPath.reserve(total);
    int bestLen = 0;

    uint64_t seed = 123456789ull + (uint64_t)N * 1000003ull +
                    (uint64_t)(r0 + 1) * 911382323ull +
                    (uint64_t)(c0 + 1) * 972663749ull;
    mt19937_64 rng(seed);

    int maxAttempts;
    if (N <= 30) maxAttempts = 50;
    else if (N <= 100) maxAttempts = 20;
    else maxAttempts = 6;

    vector<int> order(8);
    iota(order.begin(), order.end(), 0);

    auto attemptTour = [&](void) {
        fill(visited.begin(), visited.end(), 0);
        path.clear();

        int r = r0;
        int c = c0;
        visited[r * N + c] = 1;
        path.push_back({r, c});

        while (true) {
            int bestDeg = 9;
            int bestR = -1, bestC = -1;

            for (int idx = 0; idx < 8; ++idx) {
                int k = order[idx];
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                if (visited[nr * N + nc]) continue;

                int deg = 0;
                for (int t = 0; t < 8; ++t) {
                    int rr = nr + dr[t];
                    int cc = nc + dc[t];
                    if (rr < 0 || rr >= N || cc < 0 || cc >= N) continue;
                    if (!visited[rr * N + cc]) ++deg;
                }
                if (deg < bestDeg) {
                    bestDeg = deg;
                    bestR = nr;
                    bestC = nc;
                    if (bestDeg == 0) break;
                }
            }

            if (bestR == -1) break;

            r = bestR;
            c = bestC;
            visited[r * N + c] = 1;
            path.push_back({r, c});
            if ((int)path.size() == total) break;
        }

        if ((int)path.size() > bestLen) {
            bestLen = (int)path.size();
            bestPath = path;
        }
    };

    for (int attempt = 0; attempt < maxAttempts && bestLen < total; ++attempt) {
        iota(order.begin(), order.end(), 0);
        if (attempt > 0) {
            shuffle(order.begin(), order.end(), rng);
        }
        attemptTour();
    }

    if (bestLen == 0) {
        bestLen = 1;
        bestPath.clear();
        bestPath.push_back({r0, c0});
    }

    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        cout << bestPath[i].first + 1 << ' ' << bestPath[i].second + 1;
        if (i + 1 < bestLen) cout << '\n';
    }

    return 0;
}