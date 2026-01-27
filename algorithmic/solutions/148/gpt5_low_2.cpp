#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    const int N = 50;
    vector<vector<int>> t(N, vector<int>(N));
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> t[i][j];
    vector<vector<int>> p(N, vector<int>(N));
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> p[i][j];

    // Determine max tile id to size visited array
    int maxTid = 0;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) maxTid = max(maxTid, t[i][j]);
    vector<char> visited(maxTid + 1, 0);

    int ci = si, cj = sj;
    visited[t[ci][cj]] = 1;

    string ans;
    static const int di[4] = {-1, 1, 0, 0};
    static const int dj[4] = {0, 0, -1, 1};
    static const char dc[4] = {'U', 'D', 'L', 'R'};

    auto degree_unvisited = [&](int i, int j) -> int {
        int cnt = 0;
        for (int k = 0; k < 4; ++k) {
            int ni = i + di[k], nj = j + dj[k];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (t[ni][nj] == t[i][j]) continue;
            if (visited[t[ni][nj]]) continue;
            cnt++;
        }
        return cnt;
    };

    // Greedy walk until stuck
    while (true) {
        int bestK = -1;
        int bestP = -1;
        int bestDeg = -1;
        for (int k = 0; k < 4; ++k) {
            int ni = ci + di[k], nj = cj + dj[k];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (t[ni][nj] == t[ci][cj]) continue;          // cannot step within same tile
            if (visited[t[ni][nj]]) continue;              // cannot revisit a tile
            int sc = p[ni][nj];
            int deg = degree_unvisited(ni, nj);
            // Choose by score first, then by degree (to avoid dead ends), then by dir order as tiebreaker
            if (sc > bestP || (sc == bestP && deg > bestDeg)) {
                bestP = sc;
                bestDeg = deg;
                bestK = k;
            }
        }
        if (bestK == -1) break;
        ci += di[bestK];
        cj += dj[bestK];
        visited[t[ci][cj]] = 1;
        ans.push_back(dc[bestK]);
    }

    cout << ans << '\n';
    return 0;
}