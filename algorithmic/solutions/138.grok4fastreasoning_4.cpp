#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m, k;
  cin >> n >> m >> k;
  vector<string> initial(n);
  for (int i = 0; i < n; i++) cin >> initial[i];
  vector<string> target(n);
  for (int i = 0; i < n; i++) cin >> target[i];
  vector<pair<int, int>> sizes(k);
  vector<vector<string>> presets(k);
  for (int p = 0; p < k; p++) {
    int np, mp;
    cin >> np >> mp;
    sizes[p] = {np, mp};
    vector<string> f(np);
    for (int i = 0; i < np; i++) cin >> f[i];
    presets[p] = f;
  }
  auto get_id = [](char c) -> int {
    if (c >= 'a' && c <= 'z') return c - 'a';
    if (c >= 'A' && c <= 'Z') return 26 + (c - 'A');
    if (c >= '0' && c <= '9') return 52 + (c - '0');
    return -1;
  };
  vector<int> init_count(62, 0);
  for (auto& s : initial) for (char c : s) init_count[get_id(c)]++;
  vector<int> targ_count(62, 0);
  for (auto& s : target) for (char c : s) targ_count[get_id(c)]++;
  if (init_count != targ_count) {
    cout << -1 << endl;
    return 0;
  }
  vector<string> current = initial;
  vector<tuple<int, int, int>> ops;
  int dr[4] = {-1, 0, 1, 0};
  int dc[4] = {0, 1, 0, -1};
  for (int i = 1; i <= n; i++) {
    for (int j = 1; j <= m; j++) {
      char needed = target[i - 1][j - 1];
      if (current[i - 1][j - 1] == needed) continue;
      int sx = -1, sy = -1;
      bool found_source = false;
      for (int r = i; r <= n; r++) {
        int startc = (r == i ? j : 1);
        for (int c = startc; c <= m; c++) {
          if (current[r - 1][c - 1] == needed) {
            sx = r;
            sy = c;
            found_source = true;
            break;
          }
        }
        if (found_source) break;
      }
      assert(found_source);
      // BFS for path
      vector<vector<pair<int, int>>> parent(n + 1, vector<pair<int, int>>(m + 1, {-1, -1}));
      vector<vector<bool>> vis(n + 1, vector<bool>(m + 1, false));
      queue<pair<int, int>> qq;
      qq.push({sx, sy});
      vis[sx][sy] = true;
      parent[sx][sy] = {-2, -2};
      bool reached = false;
      while (!qq.empty() && !reached) {
        auto [r, c] = qq.front();
        qq.pop();
        if (r == i && c == j) {
          reached = true;
          break;
        }
        for (int d = 0; d < 4; d++) {
          int nr = r + dr[d];
          int nc = c + dc[d];
          if (nr < 1 || nr > n || nc < 1 || nc > m || vis[nr][nc]) continue;
          bool allowed = (nr > i) || (nr == i && nc >= j);
          if (!allowed) continue;
          vis[nr][nc] = true;
          parent[nr][nc] = {r, c};
          qq.push({nr, nc});
        }
      }
      assert(reached);
      // build path
      vector<pair<int, int>> path;
      pair<int, int> curp = {i, j};
      while (true) {
        path.push_back(curp);
        pair<int, int> pr = parent[curp.first][curp.second];
        if (pr.first == -2) break;
        curp = pr;
      }
      reverse(path.begin(), path.end());
      // add ops
      for (size_t st = 0; st + 1 < path.size(); st++) {
        int r1 = path[st].first, c1 = path[st].second;
        int r2 = path[st + 1].first, c2 = path[st + 1].second;
        int o, x, y;
        x = r1;
        y = c1;
        if (r1 == r2) {
          o = -1;
          if (c2 < c1) y = c2;
        } else {
          if (r2 > r1) {
            o = -4;
          } else {
            o = -3;
          }
        }
        ops.emplace_back(o, x, y);
        // swap
        swap(current[r1 - 1][c1 - 1], current[r2 - 1][c2 - 1]);
      }
    }
  }
  cout << ops.size() << endl;
  for (auto [o, x, y] : ops) {
    cout << o << " " << x << " " << y << endl;
  }
  return 0;
}