#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<vector<int>> h(N, vector<int>(N));
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      cin >> h[i][j];
    }
  }
  vector<pair<int, int>> order;
  for (int r = 0; r < N; r++) {
    if (r % 2 == 0) {
      for (int c = 0; c < N; c++) order.emplace_back(r, c);
    } else {
      for (int c = N - 1; c >= 0; c--) order.emplace_back(r, c);
    }
  }
  int NN = N * N;
  vector<string> ops;
  int cx = 0, cy = 0;
  long long cload = 0;
  auto get_move = [&](int cr, int cc, int nr, int nc) -> string {
    if (nr == cr - 1) return "U";
    if (nr == cr + 1) return "D";
    if (nc == cc + 1) return "R";
    if (nc == cc - 1) return "L";
    assert(false);
    return "";
  };
  // first pass
  for (int i = 0; i < NN; i++) {
    int r = order[i].first, c = order[i].second;
    if (h[r][c] > 0) {
      int d = h[r][c];
      ops.push_back("+" + to_string(d));
      cload += d;
      h[r][c] = 0;
    } else if (h[r][c] < 0 && cload > 0) {
      long long dd = min((long long)-h[r][c], cload);
      int d = dd;
      ops.push_back("-" + to_string(d));
      cload -= d;
      h[r][c] += d;
    }
    if (i < NN - 1) {
      int nr = order[i + 1].first, nc = order[i + 1].second;
      string m = get_move(cx, cy, nr, nc);
      ops.push_back(m);
      cx = nr;
      cy = nc;
    }
  }
  // second pass
  for (int i = NN - 1; i >= 0; i--) {
    int r = order[i].first, c = order[i].second;
    if (h[r][c] < 0 && cload > 0) {
      long long dd = min((long long)-h[r][c], cload);
      int d = dd;
      ops.push_back("-" + to_string(d));
      cload -= d;
      h[r][c] += d;
    }
    if (i > 0) {
      int pr = order[i - 1].first, pc = order[i - 1].second;
      string m = get_move(cx, cy, pr, pc);
      ops.push_back(m);
      cx = pr;
      cy = pc;
    }
  }
  for (auto& s : ops) {
    cout << s << '\n';
  }
  return 0;
}