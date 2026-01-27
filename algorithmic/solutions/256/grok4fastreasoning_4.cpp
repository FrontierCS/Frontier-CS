#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  auto query = [&](int x1, int y1, int x2, int y2) -> int {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return ans;
  };
  vector<vector<int>> grid(n + 1, vector<int>(n + 1, -1));
  grid[1][1] = 1;
  grid[n][n] = 0;
  // even BFS
  vector<vector<bool>> even_known(n + 1, vector<bool>(n + 1, false));
  even_known[1][1] = true;
  queue<pair<int, int>> q;
  q.push({1, 1});
  while (!q.empty()) {
    auto [x, y] = q.front();
    q.pop();
    // right2
    {
      int nx = x, ny = y + 2;
      if (ny <= n && (nx + ny) % 2 == 0 && !even_known[nx][ny]) {
        int ans = query(x, y, nx, ny);
        grid[nx][ny] = grid[x][y] ^ (ans == 0 ? 1 : 0);
        even_known[nx][ny] = true;
        q.push({nx, ny});
      }
    }
    // down2
    {
      int nx = x + 2, ny = y;
      if (nx <= n && (nx + ny) % 2 == 0 && !even_known[nx][ny]) {
        int