#include <bits/stdc++.h>
using namespace std;

int main() {
  vector<vector<int>> grid(30);
  for (int x = 0; x < 30; x++) {
    grid[x].resize(x + 1);
    for (int y = 0; y <= x; y++) {
      cin >> grid[x][y];
    }
  }
  vector<tuple<int, int, int, int>> swaps;
  auto sift_down = [&](auto&& self, int px, int py) -> void {
    while (true) {
      if (px == 29) break;
      int lx = px + 1, ly = py;
      int rx = px + 1, ry = py + 1;
      int val = grid[px][py];
      int sx = px, sy = py;
      if (grid[lx][ly] < val) {
        val = grid[lx][ly];
        sx = lx;
        sy = ly;
      }
      if (grid[rx][ry] < val) {
        val = grid[rx][ry];
        sx = rx;
        sy = ry;
      }
      if (sx == px && sy == py) break;
      swaps.emplace_back(px, py, sx, sy);
      swap(grid[px][py], grid[sx][sy]);
      px = sx;
      py = sy;
    }
  };
  for (int x = 28; x >= 0; x--) {
    for (int y = 0; y <= x; y++) {
      sift_down(sift_down, x, y);
    }
  }
  cout << swaps.size() << endl;
  for (auto [x1, y1, x2, y2] : swaps) {
    cout << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
  }
  return 0;
}