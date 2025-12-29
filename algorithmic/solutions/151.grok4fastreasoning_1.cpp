#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, si, sj;
  cin >> N >> si >> sj;
  vector<string> grid(N);
  for (auto& s : grid) cin >> s;
  vector<vector<int>> adj(N * N);
  int dx[4] = {-1, 0, 1, 0};
  int dy[4] = {0, 1, 0, -1};
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (grid[i][j] == '#') continue;
      int u = i * N + j;
      for (int d = 0; d < 4; d++) {
        int ni = i + dx[d];
        int nj = j + dy[d];
        if (ni < 0 || ni >= N || nj < 0 || nj >= N || grid[ni][nj] == '#') continue;
        int v = ni * N + nj;
        adj[u].push_back(v);
      }
    }
  }
  auto geti = [N](int p) { return p / N; };
  auto getj = [N](int p) { return p % N; };
  auto get_dir = [N, geti, getj](int a, int b) -> char {
    int di = geti(b) - geti(a);
    int dj = getj(b) - getj(a);
    if (di == -1 && dj == 0) return 'U';
    if (di == 1 && dj == 0) return 'D';
    if (di == 0 && dj == -1) return 'L';
    if (di == 0 && dj == 1) return 'R';
    assert(false);
    return '?';
  };
  vector<bool> vis(N * N, false);
  string route;
  function<void(int, int)> dfs = [&](int u, int par) {
    vis[u] = true;
    for (int v : adj[u]) {
      if (v == par) continue;
      if (vis[v]) continue;
      route += get_dir(u, v);
      dfs(v, u);
      route += get_dir(v, u);
    }
  };
  int start = si * N + sj;
  dfs(start, -1);
  cout << route << endl;
}