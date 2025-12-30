#include <bits/stdc++.h>
using namespace std;

int N, si, sj;
vector<string> g;
vector<vector<bool>> vis;
string ans;

const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dc[4] = {'U', 'D', 'L', 'R'};
const int inv[4] = {1, 0, 3, 2};

void dfs(int x, int y) {
    vis[x][y] = true;
    for (int k = 0; k < 4; k++) {
        int nx = x + dx[k], ny = y + dy[k];
        if (nx < 0 || nx >= N || ny < 0 || ny >= N) continue;
        if (g[nx][ny] == '#') continue;
        if (vis[nx][ny]) continue;
        ans.push_back(dc[k]);
        dfs(nx, ny);
        ans.push_back(dc[inv[k]]);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> si >> sj)) return 0;
    g.resize(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    vis.assign(N, vector<bool>(N, false));
    dfs(si, sj);

    cout << ans << '\n';
    return 0;
}