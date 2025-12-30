#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  bool has_dot[65][65] = {};
  for (int i = 0; i < M; i++) {
    int x, y;
    cin >> x >> y;
    has_dot[x][y] = true;
  }
  int c = (N - 1) / 2;
  bool hor[65][65] = {};
  bool ver[65][65] = {};
  bool dne[65][65] = {};
  bool dse[65][65] = {};
  struct Op {
    vector<pair<int, int>> verts;
    int p1_idx;
    int weight;
  };
  vector<vector<int>> operations;
  auto compute_w = [&](int x, int y) { return (x - c) * (x - c) + (y - c) * (y - c) + 1; };
  auto check_edge = [&](int x1, int y1, int x2, int y2) -> pair<bool, bool> {
    if (x1 == x2 && y1 == y2) return {true, true};
    int dx = abs(x1 - x2);
    int dy = abs(y1 - y2);
    bool is_h = (y1 == y2 && dy == 0);
    bool is_v = (x1 == x2 && dx == 0);
    bool is_d = (dx == dy && dx > 0);
    if (!(is_h || is_v || is_d)) return {false, false};
    bool u_ok = true, i_ok = true;
    int xa = min(x1, x2), xb = max(x1, x2);
    int ya, yb;
    if (is_h) {
      ya = y1;
      int len = xb - xa;
      for (int i = 0; i < len && u_ok; i++) {
        if (hor[ya][xa + i]) u_ok = false;
      }
      for (int i = 1; i < len && i_ok; i++) {
        if (has_dot[xa + i][ya]) i_ok = false;
      }
    } else if (is_v) {
      xa = x1;
      ya = min(y1, y2);
      yb = max(y1, y2);
      int len = yb - ya;
      for (int i = 0; i < len && u_ok; i++) {
        if (ver[xa][ya + i]) u_ok = false;
      }
      for (int i = 1; i < len && i_ok; i++) {
        if (has_dot[xa][ya + i]) i_ok = false;
      }
    } else {
      ya = (x1 < x2 ? y1 : y2);
      yb = (x1 < x2 ? y2 : y1);
      int len = xb - xa;
      int dy_now = yb - ya;
      bool is_ne = (dy_now == len);
      bool is_se = (dy_now == -len);
      if (!is_ne && !is_se) return {false, false};
      if (is_ne) {
        for (int i = 0; i < len && u_ok; i++) {
          int ys = ya + i;
          int xs = xa + i;
          if (dne[ys][xs]) u_ok = false;
        }
        for (int i = 1; i < len && i_ok; i++) {
          int px = xa + i, py = ya + i;
          if (has_dot[px][py]) i_ok = false;
        }
      } else {
        for (int i = 0; i < len && u_ok; i++) {
          int ys = ya - i;
          int xs = xa + i;
          if (dse[ys][xs]) u_ok = false;
        }
        for (int i = 1; i < len && i_ok; i++) {
          int px = xa + i, py = ya - i;
          if (has_dot[px][py]) i_ok = false;
        }
      }
    }
    return {u_ok, i_ok};
  };
  auto add_edge = [&](int x1, int y1, int x2, int y2) {
    int dx = abs(x1 - x2);
    int dy = abs(y1 - y2);
    bool is_h =