#include <bits/stdc++.h>

using namespace std;

int main() {
  int sx, sy;
  cin >> sx >> sy;
  vector<pair<int, int>> traps;
  if (sx + 1 <= 3000) traps.emplace_back(sx + 1, 1);
  if (sx - 1 >= 1) traps.emplace_back(sx - 1, 1);
  if (sx + 1 <= 3000) traps.emplace_back(sx + 1, 2);
  if (sx - 1 >= 1) traps.emplace_back(sx - 1, 2);
  traps.emplace_back(sx, 2);
  int idx = 0;
  int rx = sx, ry = sy;
  for (int t = 0; t < 3000; ++t) {
    int xm, ym;
    if (idx < traps.size()) {
      xm = traps[idx].first;
      ym = traps[idx].second;
      ++idx;
    } else {
      xm = min(3000, rx + 1);
      ym = min(3000, ry + 1);
    }
    cout << xm << " " << ym << endl;
    cout.flush();
    int nx, ny;
    cin >> nx >> ny;
    if (nx == 0 && ny == 0) {
      return 0;
    }
    rx = nx;
    ry = ny;
  }
  return 0;
}