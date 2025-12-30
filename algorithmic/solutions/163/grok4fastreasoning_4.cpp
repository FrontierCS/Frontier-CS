#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> original(n, vector<int>(n));
  for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) cin >> original[i][j];
  vector<bool> touches0(m + 1, false);
  for(int c = 1; c <= m; c++) {
    for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) if(original[i][j] == c) {
      if(i == 0 || i == n - 1 || j == 0 || j == n - 1) touches0[c] = true;
    }
  }
  vector<vector<bool>> adj(m + 1, vector<bool>(m + 1, false));
  int dx[4] = {0, 1, 0, -1};
  int dy[4] = {1, 0, -1, 0};
  for(int i = 0; i < n; i++) {
    for(int j = 0; j < n; j++) {
      int c = original[i][j];
      for(int dir = 0; dir < 4; dir++) {
        int ni = i + dx[dir];
        int nj = j + dy[dir];
        if(ni >= 0 && ni < n && nj >= 0 && nj < n) {
          int d = original[ni][nj];
          if(c != d && d >= 1) adj[c][d] = true;
        } else {
          touches0[c] = true;
          adj[c][0] = true;
        }
      }
    }
  }
  for(int c = 1; c <= m; c++) for(int d = 1; d <= m; d++) if(adj[c][d]) adj[d][c] = true;
  vector<vector<bool>> is_protected(n, vector<bool>(n, false));
  for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) {
    int c = original[i][j];
    if(c >= 1 && !touches0[c]) is_protected[i][j] = true;
  }
  for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) {
    if(is_protected[i][j]) continue;
    int c = original[i][j];
    if(c < 1 || !touches0[c]) continue;
    bool touch_int = false;
    for(int dir = 0; dir < 4; dir++) {
      int ni = i + dx[dir], nj = j + dy[dir];
      if(ni >= 0 && ni < n && nj >= 0 && nj < n) {
        int d = original[ni][nj];
        if(d >= 1 && !touches0[d]) {
          touch_int = true;
          break;
        }
      }
    }
    if(touch_int) is_protected[i][j] = true;
  }
  vector<vector<int>> out(n, vector<int>(n));
  for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) out[i][j] = original[i][j];
  vector<int> current_size(m + 1, 0);
  for(int c = 1; c <= m; c++) for(int i = 0; i < n; i++) for(int j = 0; j < n; j++) if(original[i][j] == c) current_size[c]++;
  queue<pair<int, int>> q;
  for(int j = 0; j < n; j++) {
    { int i = 0; int c = out[i][j]; if(c >= 1 && !is_protected[i][j] && touches0[c]) q.push({i, j}); }
    { int i = n - 1; int c = out[i][j]; if(c >= 1 && !is_protected[i][j] && touches0[c]) q.push({i, j}); }
  }
  for(int i = 1; i < n - 1; i++) {
    { int j = 0; int c = out[i][j]; if(c >= 1 && !is_protected[i][j] && touches0[c]) q.push({i, j}); }
    { int j = n - 1; int c = out[i][j]; if(c >= 1 && !is_protected[i][j] && touches0[c]) q.push({i, j}); }
  }
  while(!q.empty()) {
    auto [i, j] = q.front(); q.pop();
    if(out[i][j] == 0) continue;
    if(is_protected[i][j]) continue;
    int c = out[i][j];
    if(current_size[c] <= 1) continue;
    out[i][j] = 0;
    int si = -1, sj = -1;
    for(int x = 0; x < n; x++) {
      for(int y = 0; y < n; y++) {
        if(out[x][y] == c) {
          si = x; sj = y;
          goto found_start;
        }
      }
    }
  found_start:
    if(si == -1) {
      out[i][j] = c;
      continue;
    }
    vector<vector<bool>> vis(n, vector<bool>(n, false));
    queue<pair<int, int>> qq;
    qq.push({si, sj});
    vis[si][sj] = true;
    int reached = 1;
    vector<bool> has_touch(m + 1, false);
    while(!qq.empty()) {
      auto [x, y] = qq.front(); qq.pop();
      for(int dir = 0; dir < 4; dir++) {
        int nx = x + dx[dir];
        int ny = y + dy[dir];
        if(nx < 0 || nx >= n || ny < 0 || ny >= n) {
          has_touch[0] = true;
        } else if(out[nx][ny] == 0) {
          has_touch[0] = true;
        } else if(out[nx][ny] != c) {
          has_touch[out[nx][ny]] = true;
        }
        if(nx >= 0 && nx < n && ny >= 0 && ny < n && out[nx][ny] == c && !vis[nx][ny]) {
          vis[nx][ny] = true;
          qq.push({nx, ny});
          reached++;
        }
      }
    }
    int expected = current_size[c] - 1;
    bool conn_ok = (reached == expected);
    if(!conn_ok) {
      out[i][j] = c;
      continue;
    }
    bool touch_ok = true;
    for(int d = 0; d <= m; d++) {
      if(adj[c][d] && !has_touch[d]) {
        touch_ok = false;
        break;
      }
    }
    if(!touch_ok) {
      out[i][j] = c;
      continue;
    }
    current_size[c]--;
    for(int dir = 0; dir < 4; dir++) {
      int ni = i + dx[dir];
      int nj = j + dy[dir];
      if(ni >= 0 && ni < n && nj >= 0 && nj < n && out[ni][nj] >= 1 && !is_protected[ni][nj] && touches0[out[ni][nj]]) {
        q.push({ni, nj});
      }
    }
  }
  for(int i = 0; i < n; i++) {
    for(int j = 0; j < n; j++) {
      if(j > 0) cout << " ";
      cout << out[i][j];
    }
    cout << endl;
  }
  return 0;
}