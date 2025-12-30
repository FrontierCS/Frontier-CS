#include <bits/stdc++.h>

using namespace std;

int main() {
  int sx, sy;
  cin >> sx >> sy;
  vector<pair<int, int>> seq = {{1, 1}, {-1, 1}, {1, 2}, {-1, 2}, {0, 2}};
  int step = 0;
  const int T = 3000;
  while (step < T) {
    pair<int, int> d = seq[step % 5];
    int xm = sx + d.first;
    int ym = d.second;
    if (xm < 1) xm = 1;
    if (xm > T) xm = T;
    if (ym < 1) ym = 1;
    if (ym > T) ym = T;
    cout << xm << " " << ym << endl;
    cout.flush();
    int nx, ny;
    cin >> nx >> ny;
    if (nx == 0 && ny == 0) {
      return 0;
    }
    step++;
  }
  return 0;
}