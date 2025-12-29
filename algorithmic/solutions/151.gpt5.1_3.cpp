#include <bits/stdc++.h>
using namespace std;

int N, si, sj;
vector<string> grid;
vector<vector<int>> vis;
string path;

void dfs(int i, int j) {
    vis[i][j] = 1;
    static int di[4] = {-1, 1, 0, 0};
    static int dj[4] = {0, 0, -1, 1};
    static char dc[4] = {'U', 'D', 'L', 'R'};
    for (int k = 0; k < 4; ++k) {
        int ni = i + di[k], nj = j + dj[k];
        if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
        if (grid[ni][nj] == '#') continue;
        if (vis[ni][nj]) continue;
        path.push_back(dc[k]);
        dfs(ni, nj);
        path.push_back(dc[k ^ 1]); // opposite direction
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> si >> sj)) return 0;
    grid.assign(N, string());
    for (int i = 0; i < N; ++i) cin >> grid[i];

    vis.assign(N, vector<int>(N, 0));
    dfs(si, sj);

    cout << path << '\n';
    return 0;
}