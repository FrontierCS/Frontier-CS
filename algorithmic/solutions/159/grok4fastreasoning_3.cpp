#include <bits/stdc++.h>
using namespace std;

const int MAXN = 65;
bool has_dot[MAXN][MAXN];
bool horz[MAXN][MAXN];
bool verti[MAXN][MAXN];
bool d1[MAXN][MAXN];
bool d2[MAXN][MAXN];
int N, c;

void mark_side(int sx, int sy, int ex, int ey) {
  int dx = ex - sx;
  int dy = ey - sy;
  int adx = abs(dx);
  int ady = abs(dy);
  int minx = min(sx, ex);
  int miny = min(sy, ey);
  int maxy = max(sy, ey);
  if (dy == 0) {
    for (int i = 0; i < adx; ++i) {
      horz[minx + i][sy] = true;
    }
  } else if (dx == 0) {
    for (int i = 0; i < ady; ++i) {
      verti[sx][miny + i] = true;
    }
  } else {
    if (dx * dy > 0) {
      for (int i = 0; i < adx; ++i) {
        d1[minx + i][miny + i] = true;
      }
    } else {
      for (int i = 0; i < adx; ++i) {
        d2[minx + i][maxy - i] = true;
      }
    }
  }
}

int main() {
  int M;
  cin >> N >> M;
  c = (N - 1) / 2;
  memset(has_dot, 0, sizeof(has_dot));
  memset(horz, 0, sizeof(horz));
  memset(verti, 0, sizeof(verti));
  memset(d1, 0, sizeof(d1));
  memset(d2, 0, sizeof(d2));
  for (int i = 0; i < M; ++i) {
    int x, y;
    cin >> x >> y;
    has_dot[x][y] = true;
  }
  vector<array<int, 8>> ops;
  bool found;
  do {
    found = false;
    int best_w = -1;
    int bx1 = -1, by1 = -1, bx2 = -1, by2 = -1, bx3 = -1, by3 = -1, bx4 = -1, by4 = -1;
    // axis-aligned
    for (int x1 = 0; x1 < N; ++x1) {
      for (int x2 = x1 + 1; x2 < N; ++x2) {
        for (int y1 = 0; y1 < N; ++y1) {
          for (int y2 = y1 + 1; y2 < N; ++y2) {
            bool c1 = has_dot[x1][y1];
            bool c2 = has_dot[x2][y1];
            bool c3 = has_dot[x2][y2];
            bool c4 = has_dot[x1][y2];
            int cnt = (c1 ? 1 : 0) + (c2 ? 1 : 0) + (c3 ? 1 : 0) + (c4 ? 1 : 0);
            if (cnt == 3) {
              int mx = -1, my = -1;
              if (!c1) { mx = x1; my = y1; }
              else if (!c2) { mx = x2; my = y1; }
              else if (!c3) { mx = x2; my = y2; }
              else { mx = x1; my = y2; }
              bool clear_p = true;
              for (int xx = x1 + 1; xx < x2 && clear_p; ++xx) {
                if (has_dot[xx][y1] || has_dot[xx][y2]) clear_p = false;
              }
              for (int yy = y1 + 1; yy < y2 && clear_p; ++yy) {
                if (has_dot[x1][yy] || has_dot[x2][yy]) clear_p = false;
              }
              if (clear_p) {
                bool free_s = true;
                for (int xx = x1; xx < x2 && free_s; ++xx) {
                  if (horz[xx][y1] || horz[xx][y2]) free_s = false;
                }
                for (int yy = y1; yy < y2 && free_s; ++yy) {
                  if (verti[x1][yy] || verti[x2][yy]) free_s = false;
                }
                if (free_s) {
                  int ww = (mx - c) * (mx - c) + (my - c) * (my - c) + 1;
                  if (ww > best_w) {
                    best_w = ww;
                    int miss_idx = -1;
                    if (mx == x1 && my == y1) miss_idx = 0;
                    else if (mx == x2 && my == y1) miss_idx = 1;
                    else if (mx == x2 && my == y2) miss_idx = 2;
                    else miss_idx = 3;
                    int i2 = (miss_idx + 1) % 4;
                    int i3 = (miss_idx + 2) % 4;
                    int i4 = (miss_idx + 3) % 4;
                    bx1 = mx; by1 = my;
                    if (i2 == 0) { bx2 = x1; by2 = y1; }
                    else if (i2 == 1) { bx2 = x2; by2 = y1; }
                    else if (i2 == 2) { bx2 = x2; by2 = y2; }
                    else { bx2 = x1; by2 = y2; }
                    if (i3 == 0) { bx3 = x1; by3 = y1; }
                    else if (i3 == 1) { bx3 = x2; by3 = y1; }
                    else if (i3 == 2) { bx3 = x2; by3 = y2; }
                    else { bx3 = x1; by3 = y2; }
                    if (i4 == 0) { bx4 = x1; by4 = y1; }
                    else if (i4 == 1) { bx4 = x2; by4 = y1; }
                    else if (i4 == 2) { bx4 = x2; by4 = y2; }
                    else { bx4 = x1; by4 = y2; }
                    found = true;
                  }
                }
              }
            }
          }
        }
      }
    }
    // 45-degree
    for (int a = 1; a < N; ++a) {
      for (int b = 1; b < N; ++b) {
        int max_xx = N - 1 - a - b;
        if (max_xx < 0) continue;
        int min_yy = b;
        int max_yy = N - 1 - a;
        if (min_yy > max_yy) continue;
        for (int xx = 0; xx <= max_xx; ++xx) {
          for (int yy = min_yy; yy <= max_yy; ++yy) {
            int ax = xx, ay = yy;
            int bx_ = xx + a, by_ = yy + a;
            int cx = xx + a + b, cy = yy + a - b;
            int dx_ = xx + b, dy_ = yy - b;
            bool ca = has_dot[ax][ay];
            bool cb = has_dot[bx_][by_];
            bool cc = has_dot[cx][cy];
            bool cd = has_dot[dx_][dy_];
            int cnt = (ca ? 1 : 0) + (cb ? 1 : 0) + (cc ? 1 : 0) + (cd ? 1 : 0);
            if (cnt == 3) {
              int mx = -1, my = -1, midx = -1;
              if (!ca) { mx = ax; my = ay; midx = 0; }
              else if (!cb) { mx = bx_; my = by_; midx = 1; }
              else if (!cc) { mx = cx; my = cy; midx = 2; }
              else { mx = dx_; my = dy_; midx = 3; }
              bool clear_p = true;
              for (int i = 1; i < a && clear_p; ++i) {
                if (has_dot[xx + i][yy + i]) clear_p = false;
              }
              for (int j = 1; j < b && clear_p; ++j) {
                if (has_dot[xx + a + j][yy + a - j]) clear_p = false;
              }
              for (int k = 1; k < a && clear_p; ++k) {
                if (has_dot[xx + a + b - k][yy + a - b - k]) clear_p = false;
              }
              for (int j = 1; j < b && clear_p; ++j) {
                if (has_dot[xx + b - j][yy - b + j]) clear_p = false;
              }
              if (clear_p) {
                bool free_s = true;
                for (int i = 0; i < a && free_s; ++i) {
                  int rx = xx + i, ry = yy + i;
                  if (d1[rx][ry]) free_s = false;
                }
                for (int j = 0; j < b && free_s; ++j) {
                  int rx = xx + a + j, ry = yy + a - j;
                  if (d2[rx][ry]) free_s = false;
                }
                for (int m = 0; m < a && free_s; ++m) {
                  int rx = xx + a + b - m - 1;
                  int ry = yy + a - b - m - 1;
                  if (rx < 0 || ry < 0 || rx >= N - 1 || ry >= N - 1) {
                    free_s = false;
                  } else if (d1[rx][ry]) free_s = false;
                }
                for (int j = 0; j < b && free_s; ++j) {
                  int rx = xx + b - j - 1;
                  int ry = yy - b + j + 1;
                  if (rx < 0 || ry < 0 || rx >= N - 1 || ry >= N - 1) {
                    free_s = false;
                  } else if (d2[rx][ry]) free_s = false;
                }
                if (free_s) {
                  int ww = (mx - c) * (mx - c) + (my - c) * (my - c) + 1;
                  if (ww > best_w) {
                    best_w = ww;
                    int i2 = (midx + 1) % 4;
                    int i3 = (midx + 2) % 4;
                    int i4 = (midx + 3) % 4;
                    bx1 = mx; by1 = my;
                    if (i2 == 0) { bx2 = ax; by2 = ay; }
                    else if (i2 == 1) { bx2 = bx_; by2 = by_; }
                    else if (i2 == 2) { bx2 = cx; by2 = cy; }
                    else { bx2 = dx_; by2 = dy_; }
                    if (i3 == 0) { bx3 = ax; by3 = ay; }
                    else if (i3 == 1) { bx3 = bx_; by3 = by_; }
                    else if (i3 == 2) { bx3 = cx; by3 = cy; }
                    else { bx3 = dx_; by3 = dy_; }
                    if (i4 == 0) { bx4 = ax; by4 = ay; }
                    else if (i4 == 1) { bx4 = bx_; by4 = by_; }
                    else if (i4 == 2) { bx4 = cx; by4 = cy; }
                    else { bx4 = dx_; by4 = dy_; }
                    found = true;
                  }
                }
              }
            }
          }
        }
      }
    }
    if (found) {
      array<int, 8> op = {bx1, by1, bx2, by2, bx3, by3, bx4, by4};
      ops.push_back(op);
      has_dot[bx1][by1] = true;
      mark_side(bx1, by1, bx2, by2);
      mark_side(bx2, by2, bx3, by3);
      mark_side(bx3, by3, bx4, by4);
      mark_side(bx4, by4, bx1, by1);
    }
  } while (found);
  cout << ops.size() << endl;
  for (auto& op : ops) {
    for (int v : op) cout << v << " ";
    cout << endl;
  }
  return 0;
}