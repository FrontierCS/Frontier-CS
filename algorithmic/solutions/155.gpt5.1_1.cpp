#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    const int H = 20, W = 20;
    vector<string> h(H);     // horizontal walls: size 20 x 19
    vector<string> v(H - 1); // vertical walls: size 19 x 20

    for (int i = 0; i < H; ++i) cin >> h[i];
    for (int i = 0; i < H - 1; ++i) cin >> v[i];

    const int INF = 1e9;
    int dist[H][W];
    pair<int,int> par[H][W];
    char move_to[H][W];

    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j) {
            dist[i][j] = INF;
            par[i][j] = {-1, -1};
            move_to[i][j] = '?';
        }

    queue<pair<int,int>> q;
    dist[si][sj] = 0;
    q.push({si, sj});

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    while (!q.empty()) {
        auto [i, j] = q.front(); q.pop();
        if (i == ti && j == tj) break;

        // Up
        if (i > 0 && v[i-1][j] == '0' && dist[i-1][j] == INF) {
            dist[i-1][j] = dist[i][j] + 1;
            par[i-1][j] = {i, j};
            move_to[i-1][j] = 'U';
            q.push({i-1, j});
        }
        // Down
        if (i < H-1 && v[i][j] == '0' && dist[i+1][j] == INF) {
            dist[i+1][j] = dist[i][j] + 1;
            par[i+1][j] = {i, j};
            move_to[i+1][j] = 'D';
            q.push({i+1, j});
        }
        // Left
        if (j > 0 && h[i][j-1] == '0' && dist[i][j-1] == INF) {
            dist[i][j-1] = dist[i][j] + 1;
            par[i][j-1] = {i, j};
            move_to[i][j-1] = 'L';
            q.push({i, j-1});
        }
        // Right
        if (j < W-1 && h[i][j] == '0' && dist[i][j+1] == INF) {
            dist[i][j+1] = dist[i][j] + 1;
            par[i][j+1] = {i, j};
            move_to[i][j+1] = 'R';
            q.push({i, j+1});
        }
    }

    vector<char> path;
    int ci = ti, cj = tj;
    if (dist[ti][tj] != INF) {
        while (!(ci == si && cj == sj)) {
            char c = move_to[ci][cj];
            path.push_back(c);
            auto pcell = par[ci][cj];
            ci = pcell.first;
            cj = pcell.second;
        }
        reverse(path.begin(), path.end());
    }

    if ((int)path.size() > 200) path.resize(200);

    string ans(path.begin(), path.end());
    cout << ans << '\n';

    return 0;
}