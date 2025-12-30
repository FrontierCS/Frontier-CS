#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<vector<int>> height(N, vector<int>(N));
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      cin >> height[i][j];
    }
  }
  vector<string> ops;
  int cr = 0, cc = 0;
  long long load = 0;
  const int INF = 1e9;
  auto add_moves = [&](int tr, int tc) {
    int dc = tc - cc;
    if (dc > 0) {
      for (int k = 0; k < dc; k++) ops.push_back("R");
    } else if (dc < 0) {
      for (int k = 0; k < -dc; k++) ops.push_back("L");
    }
    int dr = tr - cr;
    if (dr > 0) {
      for (int k = 0; k < dr; k++) ops.push_back("D");
    } else if (dr < 0) {
      for (int k = 0; k < -dr; k++) ops.push_back("U");
    }
    cr = tr;
    cc = tc;
  };
  while (true) {
    bool acted = false;
    if (load > 0 && height[cr][cc] < 0) {
      long long d = min(load, (long long)-height[cr][cc]);
      ops.push_back("-" + to_string(d));
      height[cr][cc] += d;
      load -= d;
      acted = true;
    } else if (load == 0 && height[cr][cc] > 0) {
      long long d = height[cr][cc];
      ops.push_back("+" + to_string(d));
      height[cr][cc] -= d;
      load += d;
      acted = true;
    }
    if (acted) {
      continue;
    }
    bool has_source = false;
    bool has_sink = false;
    for (int r = 0; r < N; r++) {
      for (int c = 0; c < N; c++) {
        if (height[r][c] > 0) has_source = true;
        if (height[r][c] < 0) has_sink = true;
      }
    }
    if (!has_source && !has_sink) break;
    int bestr = -1, bestc = -1;
    int mind = INF;
    if (load > 0) {
      for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
          if (height[r][c] < 0) {
            int d = abs(r - cr) + abs(c - cc);
            int id = r * N + c;
            int bestid = (bestr == -1 ? INF : bestr * N + bestc);
            if (d < mind || (d == mind && id < bestid)) {
              mind = d;
              bestr = r;
              bestc = c;
            }
          }
        }
      }
      if (bestr == -1) break;
      add_moves(bestr, bestc);
    } else {
      for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
          if (height[r][c] > 0) {
            int d = abs(r - cr) + abs(c - cc);
            int id = r * N + c;
            int bestid = (bestr == -1 ? INF : bestr * N + bestc);
            if (d < mind || (d == mind && id < bestid)) {
              mind = d;
              bestr = r;
              bestc = c;
            }
          }
        }
      }
      if (bestr == -1) break;
      add_moves(bestr, bestc);
    }
  }
  for (auto &s : ops) {
    cout << s << '\n';
  }
  return 0;
}