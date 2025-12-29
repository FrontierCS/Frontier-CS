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
  vector<set<int>> adj(m + 1);
  set<int> is_boundary;
  int di[4] = {-1, 0, 1, 0};
  int dj[4] = {0, 1, 0, -1};
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      if (i == 0 || i == n - 1 || j == 0 || j == n - 1) is_boundary.insert(c);
      for (int d = 0; d < 4; d++) {
        int ni = i + di[d];
        int nj = j + dj[d];
        if (ni >= 0 && ni < n && nj >= 0 && nj < n) {
          int nc = grid[ni][nj];
          if (nc != c && nc >= 1 && nc <= m) adj[c].insert(nc);
        }
      }
    }
  }
  vector<vector<pair<int, int>>> ward_cells(m + 1);
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      int c = grid[i][j];
      ward_cells[c].push_back({i, j});
    }
  }
  vector<pair<int, int>> hubs(m + 1);
  for (int k = 1; k <= m; k++) {
    auto& cl = ward_cells[k];
    if (cl.empty()) continue;
    double si = 0, sj = 0;
    int sz = cl.size();
    for (auto p : cl) {
      si += p.first;
      sj += p.second;
    }
    double ai = si / sz;
    double aj = sj / sz;
    int md = INT_MAX;
    pair<int, int> best;
    for (auto p : cl) {
      int dd = abs(p.first - ai) + abs(p.second - aj);
      if (dd < md) {
        md = dd;
        best = p;
      }
    }
    hubs[k] = best;
  }
  set<int> boundary_set = is_boundary;
  set<int> internal_set;
  for (int k = 1; k <= m; k++) {
    if (boundary_set.count(k) == 0) internal_set.insert(k);
  }
  vector<map<int, pair<int, int>>> ports(m + 1);
  for (int k = 1; k <= m; k++) {
    if (boundary_set.count(k) == 0) continue;
    for (int d : adj[k]) {
      if (d < k) continue;
      if (boundary_set.count(d) == 0) continue;
      pair<int, int> hk = hubs[k];
      pair<int, int> hd = hubs[d];
      int min_score = INT_MAX;
      pair<int, int> best_a, best_b;
      for (int ii = 0; ii < n; ii++) {
        for (int jj = 0; jj < n; jj++) {
          if (grid[ii][jj] != k) continue;
          for (int dd = 0; dd < 4; dd++) {
            int ni = ii + di[dd];
            int nj = jj + dj[dd];
            if (ni >= 0 && ni < n && nj >= 0 && nj < n && grid[ni][nj] == d) {
              int score = abs(ii - hk.first) + abs(jj - hk.second) + abs(ni - hd.first) + abs(nj - hd.second);
              if (score < min_score) {
                min_score = score;
                best_a = {ii, jj};
                best_b = {ni, nj};
              }
            }
          }
        }
      }
      ports[k][d] = best_a;
      ports[d][k] = best_b;
    }
  }
  vector<set<pair<int, int>>> kept(m + 1);
  vector<vector<int>> par_i(m + 1, vector<int>(n * n, -1));
  vector<vector<int>> par_j(m + 1, vector<int>(n * n, -1));
  // Wait, par_i etc per ward? No, since n small, but to avoid, I'll use 2d per ward? But memory, better use map or encode.
  // Since n=50, I'll use vector<vector<int>> parx(n, vector<int>(n, -1)), pary similar, but per ward, so inside loop.
  for (int k = 1; k <= m; k++) {
    if (internal_set.count(k)) {
      for (auto p : ward_cells[k]) {
        kept[k].insert(p);
      }
      continue;
    }
    // boundary k
    set<pair<int, int>> required_ports;
    // interface
    set<pair<int, int>> interface;
    for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
        if (grid[i][j] != k) continue;
        for (int d = 0; d < 4; d++) {
          int ni = i + di[d];
          int nj = j + dj[d];
          if (ni >= 0 && ni < n && nj >= 0 && nj < n && internal_set.count(grid[ni][nj])) {
            interface.insert({i, j});
          }
        }
      }
    }
    for (auto p : interface) required_ports.insert(p);
    // ports to boundary neighbors
    auto& prt = ports[k];
    for (auto& pp : prt) {
      required_ports.insert(pp.second);
    }
    // port to 0
    pair<int, int> hk = hubs[k];
    int min_dist = INT_MAX;
    pair<int, int> best_zero = hk;
    for (auto p : ward_cells[k]) {
      int i = p.first, j = p.second;
      if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
        int dist = abs(i - hk.first) + abs(j - hk.second);
        if (dist < min_dist) {
          min_dist = dist;
          best_zero = p;
        }
      }
    }
    required_ports.insert(best_zero);
    // now, if required_ports empty? impossible
    // now, connect with BFS from hub
    vector<vector<bool>> vis(n, vector<bool>(n, false));
    vector<vector<int>> px(n, vector<int>(n, -1));
    vector<vector<int>> py(n, vector<int>(n, -1));
    queue<pair<int, int>> q;
    int hi = hk.first, hj = hk.second;
    q.push(hk);
    vis[hi][hj] = true;
    px[hi][hj] = -1;
    py[hi][hj] = -1;
    while (!q.empty()) {
      auto [x, y] = q.front();
      q.pop();
      for (int d = 0; d < 4; d++) {
        int nx = x + di[d];
        int ny = y + dj[d];
        if (nx >= 0 && nx < n && ny >= 0 && ny < n && grid[nx][ny] == k && !vis[nx][ny]) {
          vis[nx][ny] = true;
          px[nx][ny] = x;
          py[nx][ny] = y;
          q.push({nx, ny});
        }
      }
    }
    // now trace
    for (auto p : required_ports) {
      int x = p.first, y = p.second;
      while (true) {
        kept[k].insert({x, y});
        if (x == hi && y == hj) break;
        int pxv = px[x][y];
        int pyv = py[x][y];
        x = pxv;
        y = pyv;
      }
    }
  }
  // now build newgrid
  vector<vector<int>> newgrid(n, vector<int>(n, 0));
  for (int k = 1; k <= m; k++) {
    for (auto p : kept[k]) {
      newgrid[p.first][p.second] = k;
    }
  }
  // now check validity
  bool valid = true;
  // first, compute new_adj
  vector<set<int>> new_adj(m + 1);
  for (int i = 0; i < n && valid; i++) {
    for (int j = 0; j < n; j++) {
      int c = newgrid[i][j];
      if (c == 0) continue;
      for (int d = 0; d < 4; d++) {
        int ni = i + di[d];
        int nj = j + dj[d];
        if (ni >= 0 && ni < n && nj >= 0 && nj < n) {
          int nc = newgrid[ni][nj];
          if (nc > 0 && nc != c) new_adj[c].insert(nc);
        }
      }
    }
  }
  // check adjacencies
  for (int c = 1; c <= m && valid; c++) {
    for (int dc : new_adj[c]) {
      if (dc > c && adj[c].count(dc) == 0) valid = false;
    }
  }
  for (int c = 1; c <= m && valid; c++) {
    for (int dc : adj[c]) {
      if (dc > c && new_adj[c].count(dc) == 0) valid = false;
    }
  }
  // check 0 touches
  for (int k = 1; k <= m && valid; k++) {
    bool orig = is_boundary.count(k);
    bool nw = false;
    bool found = false;
    for (int i = 0; i < n && !found; i++) {
      for (int j = 0; j < n && !found; j++) {
        if (newgrid[i][j] != k) continue;
        found = true; // at least one cell
        if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
          nw = true;
          continue;
        }
        for (int d = 0; d < 4; d++) {
          int ni = i + di[d];
          int nj = j + dj[d];
          if (ni >= 0 && ni < n && nj >= 0 && nj < n && newgrid[ni][nj] == 0) {
            nw = true;
            break;
          }
        }
      }
    }
    if (nw != orig) valid = false;
  }
  // check ward connectivity
  for (int k = 1; k <= m && valid; k++) {
    vector<pair<int, int>> mycells;
    for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
        if (newgrid[i][j] == k) mycells.push_back({i, j});
      }
    }
    int num = mycells.size();
    if (num == 0) {
      valid = false;
      continue;
    }
    vector<vector<bool>> vvis(n, vector<bool>(n, false));
    queue<pair<int, int>> qq;
    auto start = mycells[0];
    qq.push(start);
    vvis[start.first][start.second] = true;
    int reached = 1;
    while (!qq.empty()) {
      auto [x, y] = qq.front();
      qq.pop();
      for (int d = 0; d < 4; d++) {
        int nx = x + di[d];
        int ny = y + dj[d];
        if (nx >= 0 && nx < n && ny >= 0 && ny < n && newgrid[nx][ny] == k && !vvis[nx][ny]) {
          vvis[nx][ny] = true;
          qq.push({nx, ny});
          reached++;
        }
      }
    }
    if (reached < num) valid = false;
  }
  // check 0 connectivity
  vector<vector<bool>> zvis(n, vector<bool>(n, false));
  queue<pair<int, int>> zq;
  for (int i = 0; i < n && valid; i++) {
    // top and bottom
    if (newgrid[0][i] == 0) {
      zq.push({0, i});
      zvis[0][i] = true;
    }
    if (newgrid[n - 1][i] == 0) {
      zq.push({n - 1, i});
      zvis[n - 1][i] = true;
    }
  }
  for (int j = 0; j < n && valid; j++) {
    // left and right, skip corners already done
    if (newgrid[j][0] == 0 && !zvis[j][0]) {
      zq.push({j, 0});
      zvis[j][0] = true;
    }
    if (newgrid[j][n - 1] == 0 && !zvis[j][n - 1]) {
      zq.push({j, n - 1});
      zvis[j][n - 1] = true;
    }
  }
  while (!zq.empty() && valid) {
    auto [x, y] = zq.front();
    zq.pop();
    for (int d = 0; d < 4; d++) {
      int nx = x + di[d];
      int ny = y + dj[d];
      if (nx >= 0 && nx < n && ny >= 0 && ny < n && newgrid[nx][ny] == 0 && !zvis[nx][ny]) {
        zvis[nx][ny] = true;
        zq.push({nx, ny});
      }
    }
  }
  bool all_zero_reached = true;
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      if (newgrid[i][j] == 0 && !zvis[i][j]) {
        all_zero_reached = false;
      }
    }
  }
  if (!all_zero_reached) valid = false;
  // if not valid, fallback
  if (!valid) {
    newgrid = grid;
  }
  // output
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      cout << newgrid[i][j];
      if (j < n - 1) cout << " ";
      else cout << "\n";
    }
  }
  return 0;
}