#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    int r, c;
    cin >> r >> c;
    r--; c--;
    vector<pair<int, int>> path;
    vector<vector<char>> vis(N, vector<char>(N, 0));
    int dx[8] = {-2, -2, -1, -1, 1, 1, 2, 2};
    int dy[8] = {-1, 1, -2, 2, -2, 2, -1, 1};
    int x = r, y = c;
    vis[x][y] = 1;
    path.push_back({x, y});
    int len = 1;
    while (len < N * N) {
        int min_deg = 9;
        int best = -1;
        for (int i = 0; i < 8; i++) {
            int nx = x + dx[i];
            int ny = y + dy[i];
            if (nx < 0 || nx >= N || ny < 0 || ny >= N || vis[nx][ny]) continue;
            int deg = 0;
            for (int j = 0; j < 8; j++) {
                int nnx = nx + dx[j];
                int nny = ny + dy[j];
                if (nnx >= 0 && nnx < N && nny >= 0 && nny < N && !vis[nnx][nny]) deg++;
            }
            if (deg < min_deg) {
                min_deg = deg;
                best = i;
            }
        }
        if (best == -1) break;
        x += dx[best];
        y += dy[best];
        vis[x][y] = 1;
        path.push_back({x, y});
        len++;
    }
    cout << len << endl;
    for (auto p : path) {
        cout << (p.first + 1) << " " << (p.second + 1) << endl;
    }
    return 0;
}