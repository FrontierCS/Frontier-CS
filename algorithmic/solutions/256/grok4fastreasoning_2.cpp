#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<vector<int>> grid(n + 1, vector<int>(n + 1, -1));
  grid[1][1] = 1;
  grid[n][n] = 0;
  auto ask = [&](int x1, int y1, int x2, int y2) -> int {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
  };
  // Determine even cells
  for (int s = 4; s <= 2 * n; s += 2) {
    int imin = max(1, s - n);
    int imax = min(n, s - 1);
    for (int i = imin; i <= imax; ++i) {
      int j = s - i;
      int pi, pj;
      if (j - 2 >= 1) {
        pi = i;
        pj = j - 2;
      } else if (i - 2 >= 1) {
        pi = i - 2;
        pj = j;
      } else {
        pi = i - 1;
        pj = j - 1;
      }
      int res = ask(pi, pj, i, j);
      grid[i][j] = (res == 1 ? grid[pi][pj] : 1 - grid[pi][pj]);
    }
  }
  // Now odds
  vector<vector<int>> delta(n + 1, vector<int>(n + 1, -1));
  vector<pair<int, int>> moves = {{0, 2}, {2, 0}, {1, 1}};
  // First tree from (1,2)
  queue<pair<int, int>> q;
  if (n >= 2) {
    delta[1][2] = 0;
    q.push({1, 2});
  }
  while (!q.empty()) {
    auto [i, j] = q.front();
    q.pop();
    for (auto [di, dj] : moves) {
      int ni = i + di, nj = j + dj;
      if (ni <= n && nj <= n && (ni + nj) % 2 == 1 && delta[ni][nj] == -1) {
        int res = ask(i, j, ni, nj);
        int nd = delta[i][j] ^ (res == 1 ? 0 : 1);
        delta[ni][nj] = nd;
        q.push({ni, nj});
      }
    }
  }
  // Second tree from (2,1)
  vector<vector<int>> temp_delta(n + 1, vector<int>(n + 1, -1));
  int xor_diff = -1;
  queue<pair<int, int>> q2;
  if (n >= 2) {
    temp_delta[2][1] = 0;
    q2.push({2, 1});
  }
  while (!q2.empty()) {
    auto [i, j] = q2.front();
    q2.pop();
    for (auto [di, dj] : moves) {
      int ni = i + di, nj = j + dj;
      if (ni > n || nj > n || (ni + nj) % 2 == 0) continue;
      bool is_new = (delta[ni][nj] == -1 && temp_delta[ni][nj] == -1);
      bool is_known = (delta[ni][nj] != -1);
      if (is_new) {
        int res = ask(i, j, ni, nj);
        int nd = temp_delta[i][j] ^ (res == 1 ? 0 : 1);
        temp_delta[ni][nj] = nd;
        q2.push({ni, nj});
      } else if (is_known && temp_delta[ni][nj] == -1 && xor_diff == -1) {
        int res = ask(i, j, ni, nj);
        xor_diff = temp_delta[i][j] ^ delta[ni][nj] ^ (res == 1 ? 0 : 1);
      }
    }
  }
  // Set delta for second tree
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      if (temp_delta[i][j] != -1 && delta[i][j] == -1) {
        delta[i][j] = temp_delta[i][j] ^ xor_diff;
      }
    }
  }
  if (n >= 2) {
    if (delta[2][1] == -1) {
      delta[2][1] = 0 ^ xor_diff;
    }
  }
  // Now distinguish
  vector<vector<int>> grid0(n + 1, vector<int>(n + 1, 0));
  vector<vector<int>> grid1(n + 1, vector<int>(n + 1, 0));
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      if ((i + j) % 2 == 0) {
        grid0[i][j] = grid[i][j];
        grid1[i][j] = grid[i][j];
      }
    }
  }
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      if ((i + j) % 2 == 1 && delta[i][j] != -1) {
        grid0[i][j] = delta[i][j];
        grid1[i][j] = 1 ^ delta[i][j];
      }
    }
  }
  // has_pal function
  auto has_pal_func = [&](const vector<vector<int>>& g, int x1, int y1, int x2, int y2) -> bool {
    vector<int> seq;
    function<bool(int, int)> dfs = [&](int x, int y) -> bool {
      seq.push_back(g[x][y]);
      bool found = false;
      if (x == x2 && y == y2) {
        int len = seq.size();
        bool is_pal = true;
        for (int k = 0; k < len / 2; ++k) {
          if (seq[k] != seq[len - 1 - k]) {
            is_pal = false;
            break;
          }
        }
        found = is_pal;
      } else {
        if (x < x2) {
          if (dfs(x + 1, y)) {
            found = true;
          }
        }
        if (!found && y < y2) {
          if (dfs(x, y + 1)) {
            found = true;
          }
        }
      }
      seq.pop_back();
      return found;
    };
    return dfs(x1, y1);
  };
  // Find distinguishing
  int qx1 = -1, qy1 = -1, qx2 = -1, qy2 = -1;
  bool h0, h1;
  bool fdiff = false;
  // Diagonal-ish
  for (int dd = 2; dd <= 12 && !fdiff; ++dd) {
    for (int dx = 0; dx <= dd && !fdiff; ++dx) {
      int dy = dd - dx;
      int ex = 1 + dx;
      int ey = 1 + dy;
      if (ex > n || ey > n) continue;
      bool has0 = has_pal_func(grid0, 1, 1, ex, ey);
      bool has1 = has_pal_func(grid1, 1, 1, ex, ey);
      if (has0 != has1) {
        fdiff = true;
        qx1 = 1;
        qy1 = 1;
        qx2 = ex;
        qy2 = ey;
        h0 = has0;
        h1 = has1;
      }
    }
  }
  // Vertical if not
  if (!fdiff) {
    for (int dd = 2; dd <= 12 && !fdiff; ++dd) {
      int ex = 1 + dd;
      int ey = 1;
      if (ex > n) continue;
      bool has0 = has_pal_func(grid0, 1, 1, ex, ey);
      bool has1 = has_pal_func(grid1, 1, 1, ex, ey);
      if (has0 != has1) {
        fdiff = true;
        qx1 = 1;
        qy1 = 1;
        qx2 = ex;
        qy2 = ey;
        h0 = has0;
        h1 = has1;
      }
    }
  }
  // Horizontal if not
  if (!fdiff) {
    for (int dd = 2; dd <= 12 && !fdiff; ++dd) {
      int ex = 1;
      int ey = 1 + dd;
      if (ey > n) continue;
      bool has0 = has_pal_func(grid0, 1, 1, ex, ey);
      bool has1 = has_pal_func(grid1, 1, 1, ex, ey);
      if (has0 != has1) {
        fdiff = true;
        qx1 = 1;
        qy1 = 1;
        qx2 = ex;
        qy2 = ey;
        h0 = has0;
        h1 = has1;
      }
    }
  }
  // Now query
  int resq = ask(qx1, qy1, qx2, qy2);
  bool actual = (resq == 1);
  if (actual == h0) {
    for (int i = 1; i <= n; ++i)
      for (int j = 1; j <= n; ++j)
        if ((i + j) % 2 == 1) grid[i][j] = grid0[i][j];
  } else {
    for (int i = 1; i <= n; ++i)
      for (int j = 1; j <= n; ++j)
        if ((i + j) % 2 == 1) grid[i][j] = grid1[i][j];
  }
  // Output
  cout << "!" << endl;
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      cout << grid[i][j];
    }
    cout << endl;
  }
  cout.flush();
  return 0;
}