#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  vector<int> flavor(101);
  for (int i = 1; i <= 100; i++) cin >> flavor[i];
  int grid[10][10];
  memset(grid, 0, sizeof(grid));
  auto apply_tilt = [](int d, int g[10][10]) {
    if (d == 0) { // F down
      for (int c = 0; c < 10; c++) {
        vector<int> cand;
        for (int r = 0; r < 10; r++) if (g[r][c]) cand.push_back(g[r][c]);
        for (int r = 0; r < 10; r++) g[r][c] = 0;
        int k = cand.size();
        for (int i = 0; i < k; i++) g[10 - k + i][c] = cand[i];
      }
    } else if (d == 1) { // B up
      for (int c = 0; c < 10; c++) {
        vector<int> cand;
        for (int r = 0; r < 10; r++) if (g[r][c]) cand.push_back(g[r][c]);
        for (int r = 0; r < 10; r++) g[r][c] = 0;
        int k = cand.size();
        for (int i = 0; i < k; i++) g[i][c] = cand[i];
      }
    } else if (d == 2) { // L left
      for (int r = 0; r < 10; r++) {
        vector<int> cand;
        for (int c = 0; c < 10; c++) if (g[r][c]) cand.push_back(g[r][c]);
        for (int c = 0; c < 10; c++) g[r][c] = 0;
        int k = cand.size();
        for (int i = 0; i < k; i++) g[r][i] = cand[i];
      }
    } else { // R right
      for (int r = 0; r < 10; r++) {
        vector<int> cand;
        for (int c = 0; c < 10; c++) if (g[r][c]) cand.push_back(g[r][c]);
        for (int c = 0; c < 10; c++) g[r][c] = 0;
        int k = cand.size();
        for (int i = 0; i < k; i++) g[r][10 - k + i] = cand[i];
      }
    }
  };
  auto compute_score = [](int g[10][10]) -> long long {
    bool vis[10][10] = {};
    long long score = 0;
    for (int r = 0; r < 10; r++) {
      for (int c = 0; c < 10; c++) {
        if (g[r][c] != 0 && !vis[r][c]) {
          int flav = g[r][c];
          int sz = 0;
          queue<pair<int, int>> q;
          q.push({r, c});
          vis[r][c] = true;
          sz = 1;
          while (!q.empty()) {
            auto [x, y] = q.front();
            q.pop();
            vector<pair<int, int>> dirs = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
            for (auto [dx, dy] : dirs) {
              int nx = x + dx, ny = y + dy;
              if (nx >= 0 && nx < 10 && ny >= 0 && ny < 10 && !vis[nx][ny] && g[nx][ny] == flav) {
                vis[nx][ny] = true;
                q.push({nx, ny});
                sz++;
              }
            }
          }
          score += 1LL * sz * sz;
        }
      }
    }
    return score;
  };
  for (int t = 1; t <= 100; t++) {
    int p;
    cin >> p;
    int cnt = 0;
    bool placed = false;
    for (int r = 0; r < 10 && !placed; r++) {
      for (int c = 0; c < 10 && !placed; c++) {
        if (grid[r][c] == 0) {
          cnt++;
          if (cnt == p) {
            grid[r][c] = flavor[t];
            placed = true;
          }
        }
      }
    }
    if (t == 100) break;
    long long best_sc = -1;
    int best_d = -1;
    char ch[] = {'F', 'B', 'L', 'R'};
    for (int d = 0; d < 4; d++) {
      int temp[10][10];
      memcpy(temp, grid, sizeof(grid));
      apply_tilt(d, temp);
      long long sc = compute_score(temp);
      if (sc > best_sc) {
        best_sc = sc;
        best_d = d;
      }
    }
    cout << ch[best_d] << endl;
    apply_tilt(best_d, grid);
  }
  return 0;
}