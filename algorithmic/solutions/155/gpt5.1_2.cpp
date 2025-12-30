#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    for (int i = 0; i < 19; ++i) cin >> v[i];

    const int H = 20, W = 20;
    static int dist[H][W];
    static int par_i[H][W];
    static int par_j[H][W];
    static char step[H][W];

    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            dist[i][j] = -1;

    queue<pair<int,int>> q;
    dist[si][sj] = 0;
    par_i[si][sj] = -1;
    par_j[si][sj] = -1;
    q.push({si, sj});

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        if (x == ti && y == tj) break;

        // Up
        if (x > 0 && v[x-1][y] == '0') {
            int nx = x - 1, ny = y;
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                par_i[nx][ny] = x;
                par_j[nx][ny] = y;
                step[nx][ny] = 'U';
                q.push({nx, ny});
            }
        }
        // Down
        if (x < H-1 && v[x][y] == '0') {
            int nx = x + 1, ny = y;
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                par_i[nx][ny] = x;
                par_j[nx][ny] = y;
                step[nx][ny] = 'D';
                q.push({nx, ny});
            }
        }
        // Left
        if (y > 0 && h[x][y-1] == '0') {
            int nx = x, ny = y - 1;
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                par_i[nx][ny] = x;
                par_j[nx][ny] = y;
                step[nx][ny] = 'L';
                q.push({nx, ny});
            }
        }
        // Right
        if (y < W-1 && h[x][y] == '0') {
            int nx = x, ny = y + 1;
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                par_i[nx][ny] = x;
                par_j[nx][ny] = y;
                step[nx][ny] = 'R';
                q.push({nx, ny});
            }
        }
    }

    string path;
    int ci = ti, cj = tj;
    while (!(ci == si && cj == sj)) {
        path.push_back(step[ci][cj]);
        int pi = par_i[ci][cj];
        int pj = par_j[ci][cj];
        ci = pi;
        cj = pj;
    }
    reverse(path.begin(), path.end());

    if ((int)path.size() > 200) {
        path.resize(200);
    }

    cout << path << '\n';
    return 0;
}