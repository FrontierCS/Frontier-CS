#include <bits/stdc++.h>
using namespace std;

int main() {
  int sx, sy;
  cin >> sx >> sy;
  vector<pair<int, int>> order;
  order.push_back({sx + 1, 1});
  if (sx > 1) order.push_back({sx - 1, 1});
  order.push_back({sx + 1, 2});
  if (sx > 1) order.push_back({sx - 1, 2});
  order.push_back({sx, 2});
  int i = 0;
  int rx = sx, ry = sy;
  while (true) {
    pair<int, int> m;
    if (i < order.size()) {
      m = order[i];
      i++;
    } else {
      m = {1, 1};
    }
    int xm = m.first, ym = m.second;
    if (xm < 1 || xm > 3000 || ym < 1 || ym > 3000) {
      xm = 1;
      ym = 1;
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