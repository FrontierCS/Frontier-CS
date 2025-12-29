#include <bits/stdc++.h>
using namespace std;

const int dr[8] = {2, 1, -1, -2, -2, -1, 1, 2};
const int dc[8] = {1, 2,  2,  1, -1, -2,-2,-1};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int sr, sc;
    if (!(cin >> N)) return 0;
    cin >> sr >> sc;
    --sr; --sc; // to 0-based

    vector<vector<char>> vis(N, vector<char>(N, 0));
    vector<pair<int,int>> bestPath;
    bestPath.reserve((size_t)N * N);
    int bestLen = 0;

    auto inb = [&](int r, int c) {
        return r >= 0 && r < N && c >= 0 && c < N;
    };

    auto degree = [&](int r, int c) {
        int cnt = 0;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (inb(nr, nc) && !vis[nr][nc]) ++cnt;
        }
        return cnt;
    };

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    const int maxTries = 4;

    vector<pair<int,int>> path;
    path.reserve((size_t)N * N);

    for (int attempt = 0; attempt < maxTries; ++attempt) {
        for (int i = 0; i < N; ++i)
            fill(vis[i].begin(), vis[i].end(), 0);

        path.clear();
        int r = sr, c = sc;

        for (int step = 0; step < N * N; ++step) {
            vis[r][c] = 1;
            path.emplace_back(r, c);
            if ((int)path.size() == N * N) break;

            int bestDeg = 9;
            int candDirs[8];
            int candCount = 0;

            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (inb(nr, nc) && !vis[nr][nc]) {
                    int deg = degree(nr, nc);
                    if (deg < bestDeg) {
                        bestDeg = deg;
                        candDirs[0] = k;
                        candCount = 1;
                    } else if (deg == bestDeg) {
                        candDirs[candCount++] = k;
                    }
                }
            }

            if (candCount == 0) break;

            int chosenDir;
            if (candCount == 1) {
                chosenDir = candDirs[0];
            } else {
                chosenDir = candDirs[rng() % candCount];
            }
            r += dr[chosenDir];
            c += dc[chosenDir];
        }

        if ((int)path.size() > bestLen) {
            bestLen = (int)path.size();
            bestPath = path;
        }
        if (bestLen == N * N) break;
    }

    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        cout << bestPath[i].first + 1 << ' ' << bestPath[i].second + 1;
        if (i + 1 < bestLen) cout << '\n';
    }

    return 0;
}