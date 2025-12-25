#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    int r, c;
    cin >> r >> c;
    r--; c--;
    vector<vector<char>> vis(N, vector<char>(N, 0));
    vector<pair<int, int>> path;
    path.push_back({r, c});
    vis[r][c] = 1;
    int curx = r, cury = c;
    int dx[8] = {-2, -2, -1, -1, 1, 1, 2, 2};
    int dy[8] = {-1, 1, -2, 2, -2, 2, -1, 1};
    int len = 1;
    while (len < N * N) {
        int best_deg = 9;
        int bx = -1, by = -1, bd = -1;
        for (int d = 0; d < 8; d++) {
            int nx = curx + dx[d];
            int ny = cury + dy[d];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N && !vis[nx][ny]) {
                int deg = 0;
                for (int dd = 0; dd < 8; dd++) {
                    int nnx = nx + dx[dd];
                    int nny = ny + dy[dd];
                    if (nnx >= 0 && nnx < N && nny >= 0 && nny < N && !vis[nnx][nny]) deg++;
                }
                if (deg < best_deg || (deg == best_deg && d < bd)) {
                    best_deg = deg;
                    bx = nx;
                    by = ny;
                    bd = d;
                }
            }
        }
        if (bx == -1) break;
        vis[bx][by] = 1;
        path.push_back({bx, by});
        curx = bx;
        cury = by;
        len++;
    }
    cout << len << '\n';
    for (auto p : path) {
        cout << (p.first + 1) << " " << (p.second + 1) << '\n';
    }
    return 0;
}