#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N;
  cin >> N;
  int r, c;
  cin >> r >> c;
  vector<vector<char>> visited(N + 1, vector<char>(N + 1, 0));
  vector<pair<int, int>> path;
  path.emplace_back(r, c);
  visited[r][c] = 1;
  int dx[8] = {1, 1, -1, -1, 2, 2, -2, -2};
  int dy[8] = {2, -2, 2, -2, 1, -1, 1, -1};
  pair<int, int> cur = {r, c};
  while (true) {
    vector<pair<int, int>> cands;
    for (int d = 0; d < 8; d++) {
      int nx = cur.first + dx[d];
      int ny = cur.second + dy[d];
      if (nx >= 1 && nx <= N && ny >= 1 && ny <= N && visited[nx][ny] == 0) {
        cands.emplace_back(nx, ny);
      }
    }
    if (cands.empty()) break;
    vector<tuple<int, int, int>> scored;
    for (auto& p : cands) {
      int x = p.first, y = p.second;
      int deg = 0;
      for (int d = 0; d < 8; d++) {
        int nx = x + dx[d];
        int ny = y + dy[d];
        if (nx >= 1 && nx <= N && ny >= 1 && ny <= N && visited[nx][ny] == 0) deg++;
      }
      scored.emplace_back(deg, x, y);
    }
    sort(scored.begin(), scored.end());
    auto [deg, nx, ny] = scored[0];
    path.emplace_back(nx, ny);
    visited[nx][ny] = 1;
    cur = {nx, ny};
  }
  cout << path.size() << "\n";
  for (auto& p : path) {
    cout << p.first << " " << p.second << "\n";
  }
  return 0;
}