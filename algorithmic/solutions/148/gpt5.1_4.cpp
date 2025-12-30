#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;

    static int t[N][N], p[N][N];
    int maxT = -1;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> t[i][j];
            if (t[i][j] > maxT) maxT = t[i][j];
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> p[i][j];
        }
    }

    int M = maxT + 1;
    vector<char> visited(M, 0);
    visited[t[si][sj]] = 1;

    int ci = si, cj = sj;
    vector<char> ans;
    ans.reserve(M);

    auto inside = [&](int x, int y) {
        return 0 <= x && x < N && 0 <= y && y < N;
    };

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    while (true) {
        int bestDir = -1;
        int bestScore = -1;

        for (int d = 0; d < 4; ++d) {
            int ni = ci + di[d];
            int nj = cj + dj[d];
            if (!inside(ni, nj)) continue;
            int tileId = t[ni][nj];
            if (visited[tileId]) continue;

            int candTile = tileId;
            int deg = 0;
            for (int e = 0; e < 4; ++e) {
                int xi = ni + di[e];
                int xj = nj + dj[e];
                if (!inside(xi, xj)) continue;
                int tid = t[xi][xj];
                if (tid == candTile) continue;
                if (visited[tid]) continue;
                ++deg;
            }
            int curScore = p[ni][nj] * 100 + deg;
            if (curScore > bestScore) {
                bestScore = curScore;
                bestDir = d;
            }
        }

        if (bestDir == -1) break;

        ci += di[bestDir];
        cj += dj[bestDir];
        visited[t[ci][cj]] = 1;
        ans.push_back(dc[bestDir]);
    }

    for (char c : ans) cout << c;
    cout << '\n';

    return 0;
}