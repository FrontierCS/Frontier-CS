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
  vector<bool> touch_0(m + 1, false);
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (i == 0 || i == n - 1 || j == 0 || j == n - 1) touch_0[c] = true;
    }
  }
  vector<vector<bool>> is_adj(m + 1, vector<bool>(m + 1, false));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (j + 1 < n) {
        int d = grid[i][j + 1];
        if (c != d) {
          is_adj[c][d] = true;
          is_adj[d][c] = true;
        }
      }
      if (i + 1 < n) {
        int d = grid[i + 1][j];
        if (c != d) {
          is_adj[c][d] = true;
          is_adj[d][c] = true;
        }
      }
    }
  }
  vector<vector<int>> touch_cnt(m + 1, vector<int>(m + 1, 0));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (j + 1 < n) {
        int d = grid[i][j + 1];
        touch_cnt[c][d]++;
        touch_cnt[d][c]++;
      }
      if (i + 1 < n) {
        int d = grid[i + 1][j];
        touch_cnt[c][d]++;
        touch_cnt[d][c]++;
      }
    }
  }
  queue<pair<int, int>> q;
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (touch_0[c] && (i == 0 || i == n - 1 || j == 0 || j == n - 1)) {
        q.push({i, j});
      }
    }
  }
  int dx[4] = {-1, 0, 1, 0};
  int dy[4] = {0, 1, 0, -1};
  while (!q.empty()) {
    auto [x, y] = q.front();
    q.pop();
    if (grid[x][y] == 0) continue;
    int c = grid[x][y];
    if (!touch_0[c]) continue;
    bool is_adj_zero = false;
    for (int d = 0; d < 4; d++) {
      int nx = x + dx[d];
      int ny = y + dy[d];
      if (nx < 0 || nx >= n || ny < 0 || ny >= n || grid[nx][ny] == 0) {
        is_adj_zero = true;
        break;
      }
    }
    if (!is_adj_zero) continue;
    vector<int> sub(m + 1, 0);
    for (int d = 0; d < 4; d++) {
      int nx = x + dx[d];
      int ny = y + dy[d];
      if (nx >= 0 && nx < n && ny >= 0 && ny < n) {
        int dd = grid[nx][ny];
        if (dd != 0 && dd != c) {
          sub[dd]++;
        }
      }
    }
    bool ok_touch = true;
    for (int dd = 1; dd <= m; dd++) {
      if (sub[dd] > 0) {
        int after = touch_cnt[c][dd] - sub[dd];
        if (after == 0 && is_adj[c][dd]) {
          ok_touch = false;
          break;
        }
      }
    }
    if (!ok_touch) continue;
    bool touch_int = false;
    for (int d = 0; d < 4; d++) {
      int nx = x + dx[d];
      int ny = y + dy[d];
      if (nx >= 0 && nx < n && ny >= 0 && ny < n) {
        int dd = grid[nx][ny];
        if (dd != 0 && dd != c && !touch_0[dd]) {
          touch_int = true;
          break;
        }
      }
    }
    if (touch_int) continue;
    grid[x][y] = 0;
    pair<int, int> start_pos = {-1, -1};
    bool has_c = false;
    for (int ii = 0; ii < n; ii++) {
      for (int jj = 0; jj < n; jj++) {
        if (grid[ii][jj] == c) {
          has_c = true;
          start_pos = {ii, jj};
          goto found_start;
        }
      }
    }
  found_start:;
    bool conn = false;
    bool has_t0 = false;
    if (!has_c) {
      grid[x][y] = c;
      continue;
    }
    vector<vector<bool>> visited(n, vector<bool>(n, false));
    queue<pair<int, int>> bqueue;
    bqueue.push(start_pos);
    visited[start_pos.first][start_pos.second] = true;
    int vcount = 1;
    while (!bqueue.empty()) {
      auto [cx, cy] = bqueue.front();
      bqueue.pop();
      for (int d = 0; d < 4; d++) {
        int nx = cx + dx[d];
        int ny = cy + dy[d];
        if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] == c && !visited[nx][ny]) {
          visited[nx][ny] = true;
          bqueue.push({nx, ny});
          vcount++;
        }
      }
    }
    int tcount = 0;
    for (int ii = 0; ii < n; ii++) {
      for (int jj = 0; jj < n; jj++) {
        if (grid[ii][jj] == c) tcount++;
      }
    }
    conn = (vcount == tcount);
    if (conn) {
      has_t0 = false;
      for (int ii = 0; ii < n && !has_t0; ii++) {
        for (int jj = 0; jj < n && !has_t0; jj++) {
          if (grid[ii][jj] == c) {
            bool cell_t0 = false;
            for (int d = 0; d < 4; d++) {
              int nx = ii + dx[d];
              int ny = jj + dy[d];
              if (nx < 0 || nx >= n || ny < 0 || ny >= n || grid[nx][ny] == 0) {
                cell_t0 = true;
                break;
              }
            }
            if (cell_t0) {
              has_t0 = true;
            }
          }
        }
      }
    }
    if (conn && has_t0 && has_c) {
      for (int dd = 1; dd <= m; dd++) {
        if (sub[dd] > 0) {
          touch_cnt[c][dd] -= sub[dd];
          touch_cnt[dd][c] -= sub[dd];
        }
      }
      for (int d = 0; d < 4; d++) {
        int nx = x + dx[d];
        int ny = y + dy[d];
        if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] != 0) {
          q.push({nx, ny});
        }
      }
    } else {
      grid[x][y] = c;
    }
  }
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      if (j > 0) cout << " ";
      cout << grid[i][j];
    }
    cout << endl;
  }
  return 0;
}