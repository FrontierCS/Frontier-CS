#include <bits/stdc++.h>
using namespace std;

int dfs(int r, int c, int fl, const vector<vector<int>>& g, vector<vector<bool>>& vis) {
  vis[r][c] = true;
  int sz = 1;
  int dr[] = {-1, 0, 1, 0};
  int dc[] = {0, 1, 0, -1};
  for (int d = 0; d < 4; d++) {
    int nr = r + dr[d], nc = c + dc[d];
    if (nr >= 0 && nr < 10 && nc >= 0 && nc < 10 && g[nr][nc] == fl && !vis[nr][nc]) {
      sz += dfs(nr, nc, fl, g, vis);
    }
  }
  return sz;
}

long long compute_score(const vector<vector<int>>& g) {
  long long total = 0;
  for (int fl = 1; fl <= 3; fl++) {
    vector<vector<bool>> vis(10, vector<bool>(10, false));
    long long sumsq = 0;
    for (int r = 0; r < 10; r++) {
      for (int c = 0; c < 10; c++) {
        if (g[r][c] == fl && !vis[r][c]) {
          int sz = dfs(r, c, fl, g, vis);
          sumsq += 1LL * sz * sz;
        }
      }
    }
    total += sumsq;
  }
  return total;
}

vector<vector<int>> simulate_tilt(const vector<vector<int>>& orig, char dir) {
  vector<vector<int>> ng(10, vector<int>(10, 0));
  if (dir == 'L' || dir == 'R') {
    for (int r = 0; r < 10; r++) {
      vector<int> lst;
      for (int c = 0; c < 10; c++) {
        if (orig[r][c] != 0) lst.push_back(orig[r][c]);
      }
      int sz = lst.size();
      if (dir == 'L') {
        for (int i = 0; i < sz; i++) {
          ng[r][i] = lst[i];
        }
      } else {
        for (int i = 0; i < sz; i++) {
          ng[r][10 - sz + i] = lst[i];
        }
      }
    }
  } else {
    for (int c = 0; c < 10; c++) {
      vector<int> lst;
      for (int r = 0; r < 10; r++) {
        if (orig[r][c] != 0) lst.push_back(orig[r][c]);
      }
      int sz = lst.size();
      if (dir == 'F') {
        for (int i = 0; i < sz; i++) {
          ng[i][c] = lst[i];
        }
      } else {
        for (int i = 0; i < sz; i++) {
          ng[10 - sz + i][c] = lst[i];
        }
      }
    }
  }
  return ng;
}

int main() {
  vector<int> flavors(101);
  for (int t = 1; t <= 100; t++) {
    cin >> flavors[t];
  }
  vector<vector<int>> grid(10, vector<int>(10, 0));
  for (int t = 1; t <= 100; t++) {
    int p;
    cin >> p;
    int count = 0;
    bool placed = false;
    for (int r = 0; r < 10 && !placed; r++) {
      for (int c = 0; c < 10 && !placed; c++) {
        if (grid[r][c] == 0) {
          count++;
          if (count == p) {
            grid[r][c] = flavors[t];
            placed = true;
          }
        }
      }
    }
    if (t < 100) {
      vector<pair<long long, char>> opts;
      string dirs = "FBLR";
      for (char d : dirs) {
        auto ng = simulate_tilt(grid, d);
        long long sc = compute_score(ng);
        opts.emplace_back(sc, d);
      }
      sort(opts.rbegin(), opts.rend());
      char chosen = opts[0].second;
      cout << chosen << endl;
      cout.flush();
      grid = simulate_tilt(grid, chosen);
    }
  }
  return 0;
}