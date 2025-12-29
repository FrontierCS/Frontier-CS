#include <bits/stdc++.h>
using namespace std;

void rearrange(vector<vector<char>>& grid, const vector<vector<char>>& goal, vector<array<int, 3>>& ops, int n, int m) {
  int di[4] = {0, 0, 1, -1};
  int dj[4] = {1, -1, 0, 0};
  auto is_unfixed = [&](int r0, int c0, int x, int y) -> bool {
    if (x > r0) return true;
    if (x < r0) return false;
    return y >= c0;
  };
  for (int r = 0; r < n; r++) {
    for (int cc = 0; cc < m; cc++) {
      if (grid[r][cc] == goal[r][cc]) continue;
      char needed = goal[r][cc];
      pair<int, int> source = {-1, -1};
      for (int i = r; i < n; i++) {
        int startj = (i == r ? cc + 1 : 0);
        for (int j = startj; j < m; j++) {
          if (grid[i][j] == needed) {
            source = {i, j};
            goto found_source;
          }
        }
      }
    found_source:;
      assert(source.first != -1);
      vector<vector<bool>> vis(n, vector<bool>(m, false));
      vector<vector<pair<int, int>>> pre(n, vector<pair<int, int>>(m, {-1, -1}));
      queue<pair<int, int>> q;
      q.push({r, cc});
      vis[r][cc] = true;
      while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (int d = 0; d < 4; d++) {
          int nx = x + di[d];
          int ny = y + dj[d];
          if (nx >= 0 && nx < n && ny >= 0 && ny < m && !vis[nx][ny] &&
              is_unfixed(r, cc, nx, ny)) {
            vis[nx][ny] = true;
            pre[nx][ny] = {x, y};
            q.push({nx, ny});
          }
        }
      }
      assert(vis[source.first][source.second]);
      vector<pair<int, int>> path;
      for (auto at = source; at.first != -1; at = pre[at.first][at.second]) {
        path.push_back(at);
      }
      reverse(path.begin(), path.end());
      for (int st = (int)path.size() - 2; st >= 0; st--) {
        auto [x1, y1] = path[st];
        auto [x2, y2] = path[st + 1];
        swap(grid[x1][y1], grid[x2][y2]);
        int op_type, opx, opy;
        if (x1 == x2) {
          if (y1 < y2) {
            op_type = -1;
            opx = x1 + 1;
            opy = y1 + 1;
          } else {
            op_type = -2;
            opx = x1 + 1;
            opy = y1 + 1;
          }
        } else {
          if (x1 < x2) {
            op_type = -4;
            opx = x1 + 1;
            opy = y1 + 1;
          } else {
            op_type = -3;
            opx = x1 + 1;
            opy = y1 + 1;
          }
        }
        ops.push_back({op_type, opx, opy});
      }
      assert(grid[r][cc] == needed);
    }
  }
}

int main() {
  int n, m, k;
  cin >> n >> m >> k;
  vector<vector<char>> init(n, vector<char>(m));
  for (int i = 0; i < n; i++) {
    string s;
    cin >> s;
    for (int j = 0; j < m; j++) init[i][j] = s[j];
  }
  vector<vector<char>> targ(n, vector<char>(m));
  for (int i = 0; i < n; i++) {
    string s;
    cin >> s;
    for (int j = 0; j < m; j++) targ[i][j] = s[j];
  }
  vector<vector<vector<char>>> presets(k);
  vector<pair<int, int>> sizes(k);
  for (int p = 0; p < k; p++) {
    int np, mp;
    cin >> np >> mp;
    sizes[p] = {np, mp};
    vector<vector<char>> f(np, vector<char>(mp));
    for (int i = 0; i < np; i++) {
      string s;
      cin >> s;
      for (int j = 0; j < mp; j++) f[i][j] = s[j];
    }
    presets[p] = f;
  }
  int freq_init[128] = {0};
  int freq_targ[128] = {0};
  for (int i = 0; i < n; i++)
    for (int j = 0; j < m; j++) {
      freq_init[(unsigned char)init[i][j]]++;
      freq_targ[(unsigned char)targ[i][j]]++;
    }
  bool match = true;
  for (int i = 0; i < 128; i++)
    if (freq_init[i] != freq_targ[i]) match = false;
  vector<array<int, 3>> ops;
  vector<vector<char>> grid = init;
  bool solved = false;
  if (match) {
    rearrange(grid, targ, ops, n, m);
    solved = true;
  } else {
    for (int p = 0; p < k; p++) {
      int np = sizes[p].first;
      int mp = sizes[p].second;
      int si = np * mp;
      int f_freq[128] = {0};
      for (auto& row : presets[p])
        for (char ch : row) f_freq[(unsigned char)ch]++;
      int r_freq[128] = {0};
      int sum_r = 0;
      bool poss = true;
      for (int cc = 0; cc < 128; cc++) {
        int rc = freq_init[cc] + f_freq[cc] - freq_targ[cc];
        if (rc < 0) {
          poss = false;
          break;
        }
        r_freq[cc] = rc;
        sum_r += rc;
      }
      if (!poss || sum_r != si) continue;
      bool ok = true;
      for (int cc = 0; cc < 128; cc++) {
        if (r_freq[cc] > freq_init[cc]) {
          ok = false;
          break;
        }
      }
      if (!ok) continue;
      // found
      solved = true;
      // build lists
      vector<char> discard_list;
      for (int cc = 0; cc < 128; cc++) {
        for (int t = 0; t < r_freq[cc]; t++) {
          discard_list.push_back((char)cc);
        }
      }
      vector<char> keep_list;
      for (int cc = 0; cc < 128; cc++) {
        int numk = freq_init[cc] - r_freq[cc];
        for (int t = 0; t < numk; t++) {
          keep_list.push_back((char)cc);
        }
      }
      // temp target, place at 0,0
      vector<vector<char>> temp(n, vector<char>(m));
      int idxin = 0, idxout = 0;
      for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
          bool inside = (i < np && j < mp);
          if (inside) {
            temp[i][j] = discard_list[idxin++];
          } else {
            temp[i][j] = keep_list[idxout++];
          }
        }
      }
      // first rearrange init to temp
      grid = init;  // reset
      rearrange(grid, temp, ops, n, m);
      // add preset op
      ops.push_back({p + 1, 1, 1});
      // apply preset to grid
      for (int a = 0; a < np; a++) {
        for (int b = 0; b < mp; b++) {
          grid[a][b] = presets[p][a][b];
        }
      }
      // second rearrange to targ
      rearrange(grid, targ, ops, n, m);
      break;
    }
  }
  if (!solved) {
    cout << -1 << endl;
    return 0;
  }
  cout << ops.size() << endl;
  for (auto& ar : ops) {
    cout << ar[0] << " " << ar[1] << " " << ar[2] << endl;
  }
  return 0;
}