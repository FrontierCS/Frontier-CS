#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  int h = n / m;
  vector<vector<int>> stacks(m);
  vector<pair<int, int>> location(n + 1, {-1, -1});
  for (int i = 0; i < m; i++) {
    stacks[i].resize(h);
    for (int j = 0; j < h; j++) {
      cin >> stacks[i][j];
      location[stacks[i][j]] = {i, j};
    }
  }
  vector<pair<int, int>> ops;
  for (int v = 1; v <= n; v++) {
    int s = location[v].first;
    int p = location[v].second;
    size_t cs = stacks[s].size();
    if (p == (int)cs - 1) {
      ops.emplace_back(v, 0);
      stacks[s].pop_back();
      location[v] = {-1, -1};
    } else {
      int q = p + 1;
      int u = stacks[s][q];
      int best_t = -1;
      for (int tt = 0; tt < m; tt++) {
        if (tt != s && stacks[tt].empty()) {
          best_t = tt;
          break;
        }
      }
      if (best_t == -1) {
        int max_top_val = -1;
        best_t = -1;
        for (int tt = 0; tt < m; tt++) {
          if (tt != s && !stacks[tt].empty()) {
            int tp = stacks[tt].back();
            if (tp > max_top_val || (tp == max_top_val && tt < best_t)) {
              max_top_val = tp;
              best_t = tt;
            }
          }
        }
      }
      int t = best_t;
      vector<int> moved;
      size_t old_size = stacks[s].size();
      for (size_t jj = q; jj < old_size; jj++) {
        moved.push_back(stacks[s][jj]);
      }
      stacks[s].resize(q);
      size_t old_t_size = stacks[t].size();
      for (size_t ii = 0; ii < moved.size(); ii++) {
        int box = moved[ii];
        location[box] = {t, (int)(old_t_size + ii)};
      }
      for (int b : moved) {
        stacks[t].push_back(b);
      }
      ops.emplace_back(u, t + 1);
      ops.emplace_back(v, 0);
      stacks[s].pop_back();
      location[v] = {-1, -1};
    }
  }
  for (auto [vv, ii] : ops) {
    cout << vv << " " << ii << "\n";
  }
  return 0;
}