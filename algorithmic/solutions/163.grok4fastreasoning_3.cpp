#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> grid(n, vector<int>(n));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      cin >> grid[i][j];
    }
  }
  vector<vector<int>> out_grid = grid;
  vector<bool> touches0(m + 1, false);
  for (int i = 0; i < n; i++) {
    touches0[grid[0][i]] = true;
    touches0[grid[n - 1][i]] = true;
    touches0[grid[i][0]] = true;
    touches0[grid[i][n - 1]] = true;
  }
  vector<vector<int>> touch_count(m + 1, vector<int>(m + 1, 0));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (j + 1 < n) {
        int d = grid[i][j + 1];
        if (c > 0 && d > 0 && c != d) {
          touch_count[c][d]++;
          touch_count[d][c]++;
        }
      }
      if (i + 1 < n) {
        int d = grid[i + 1][j];
        if (c > 0 && d > 0 && c != d) {
          touch_count[c][d]++;
          touch_count[d][c]++;
        }
      }
    }
  }
  vector<vector<bool>> must_keep(n, vector<bool>(n, false));
  vector<bool> has_protected(m + 1, false);
  for (int j = 0; j < n; j++) {
    int c = grid[0][j];
    if (touches0[c] && !has_protected[c]) {
      must_keep[0][j] = true;
      has_protected[c] = true;
    }
  }
  for (int j = 0; j < n; j++) {
    int c = grid[n - 1][j];
    if (touches0[c] && !has_protected[c]) {
      must_keep[n - 1][j] = true;
      has_protected[c] = true;
    }
  }
  for (int i = 0; i < n; i++) {
    int c = grid[i][0];
    if (touches0[c] && !has_protected[c]) {
      must_keep[i][0] = true;
      has_protected[c] = true;
    }
  }
  for (int i = 0; i < n; i++) {
    int c = grid[i][n - 1];
    if (touches0[c] && !has_protected[c]) {
      must_keep[i][n - 1] = true;
      has_protected[c] = true;
    }
  }
  int dx[4] = {-1, 0, 1, 0};
  int dy[4] = {0, 1, 0, -1};
  auto adj_to_zero = [&](int x, int y) -> bool {
    if (x == 0 || x == n - 1 || y == 0 || y == n - 1) return true;
    for (int d = 0; d < 4; d++) {
      int nx = x + dx[d], ny = y + dy[d];
      if (out_grid[nx][ny] == 0) return true;
    }
    return false;
  };
  bool changed = true;
  while (changed) {
    changed = false;
    for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
        if (out_grid[i][j] == 0) continue;
        if (!adj_to_zero(i, j)) continue;
        if (must_keep[i][j]) continue;
        int c = out_grid[i][j];
        int deg = 0;
        for (int d = 0; d < 4; d++) {
          int ni = i + dx[d], nj = j + dy[d];
          if (ni >= 0 && ni < n && nj >= 0 && nj < n && out_grid[ni][nj] == c) deg++;
        }
        if (deg == 0 || deg >= 2) continue;
        vector<int> contrib(m + 1, 0);
        bool would_internal = false;
        for (int d = 0; d < 4; d++) {
          int ni = i + dx[d], nj = j + dy[d];
          if (ni >= 0 && ni < n && nj >= 0 && nj < n) {
            int nc = out_grid[ni][nj];
            if (nc > 0 && nc != c) {
              contrib[nc]++;
              if (!touches0[nc]) would_internal = true;
            }
          }
        }
        bool safe = true;
        for (int nc = 1; nc <= m; nc++) {
          if (contrib[nc] > 0 && touch_count[c][nc] == contrib[nc]) {
            safe = false;
            break;
          }
        }
        if (!safe || would_internal) continue;
        out_grid[i][j] = 0;
        changed = true;
        for (int nc = 1; nc <= m; nc++) {
          if (contrib[nc] > 0) {
            touch_count[c][nc] -= contrib[nc];
            touch_count[nc][c] -= contrib[nc];
          }
        }
      }
    }
  }
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      cout << out_grid[i][j];
      if (j < n - 1) cout << " ";
      else cout << "\n";
    }
  }
  return 0;
}