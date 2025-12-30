#include <bits/stdc++.h>
using namespace std;

int N, si, sj;
vector<string> grid;
vector<vector<bool>> visited;
string route;

int dy[4] = {-1, 1, 0, 0};
int dx[4] = {0, 0, -1, 1};
char dirCh[4] = {'U', 'D', 'L', 'R'};
char revCh[4] = {'D', 'U', 'R', 'L'};

void dfs(int y, int x) {
    visited[y][x] = true;
    for (int d = 0; d < 4; d++) {
        int ny = y + dy[d];
        int nx = x + dx[d];
        if (ny < 0 || ny >= N || nx < 0 || nx >= N) continue;
        if (grid[ny][nx] == '#') continue;
        if (visited[ny][nx]) continue;
        route.push_back(dirCh[d]);
        dfs(ny, nx);
        route.push_back(revCh[d]);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> si >> sj;
    grid.resize(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    visited.assign(N, vector<bool>(N, false));
    dfs(si, sj);

    cout << route << '\n';
    return 0;
}