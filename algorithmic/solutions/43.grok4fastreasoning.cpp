#include <bits/stdc++.h>
using namespace std;

int main() {
  int n = 50, m = 50;
  vector<string> g(n, string(m, '#'));
  vector<pair<int, int>> path;
  bool right_dir = true;
  for (int i = 0; i < 24; i++) {
    int rr = 2 * i;
    int sc = right_dir ? 0 : m - 1;
    int step = right_dir ? 1 : -1;
    for (int j = 0; j < m; j++) {
      int cc = sc + j * step;
      path.emplace_back(rr, cc);
    }
    if (i < 23) {
      int end_cc = right_dir ? m - 1 : 0;
      int crr = 2 * i + 1;
      path.emplace_back(crr, end_cc);
    }
    right_dir = !right_dir;
  }
  // add final parts
  path.emplace_back(47, 0);
  path.emplace_back(48, 0);
  path.emplace_back(49, 0);
  // set path cells
  for (const auto& p : path) {
    int r = p.first, c = p.second;
    g[r][c] = '.';
  }
  // set P
  int pr = path[0].first, pc = path[0].second;
  g[pr][pc] = 'P';
  // set B
  g[48][1] = 'B'; g[48][2] = 'B';
  g[49][1] = 'B'; g[49][2] = 'B';
  // set S
  g[48][3] = 'S'; g[48][4] = 'S';
  g[49][3] = 'S'; g[49][4] = 'S';
  // output
  cout << n << " " << m << endl;
  for (const auto& s : g) {
    cout << s << endl;
  }
  return 0;
}