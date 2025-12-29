#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> stacks(m);
  for (int i = 0; i < m; i++) {
    stacks[i].resize(n / m);
    for (int j = 0; j < n / m; j++) {
      cin >> stacks[i][j];
    }
  }
  vector<pair<int, int>> ops;
  auto choose_target = [&](int avoid) -> int {
    int min_h = INT_MAX;
    int best = -1;
    for (int i = 0; i < m; i++) {
      if (i == avoid) continue;
      int hh = stacks[i].size();
      if (hh < min_h || (hh == min_h && i < best)) {
        min_h = hh;
        best = i;
      }
    }
    return best;
  };
  for (int current = 1; current <= n; current++) {
    int s = -1, pos = -1;
    for (int i = 0; i < m; i++) {
      for (int p = 0; p < stacks[i].size(); p++) {
        if (stacks[i][p] == current) {
          s = i;
          pos = p;
          goto found;
        }
      }
    }
  found:;
    assert(s != -1);
    int sz = stacks[s].size();
    int h = sz - pos - 1;
    if (h == 0) {
      ops.emplace_back(current, 0);
      stacks[s].pop_back();
      continue;
    }
    int nextv = current + 1;
    bool has_next = false;
    int pos_next = -1;
    if (nextv <= n) {
      for (int p = pos + 1; p < sz; p++) {
        if (stacks[s][p] == nextv) {
          has_next = true;
          pos_next = p;
          break;
        }
      }
    }
    int t;
    if (!has_next) {
      int v_op = stacks[s][pos + 1];
      t = choose_target(s);
      ops.emplace_back(v_op, t + 1);
      vector<int> suffix(stacks[s].begin() + pos + 1, stacks[s].end());
      stacks[s].resize(pos + 1);
      for (int x : suffix) stacks[t].push_back(x);
    } else {
      int lower_start = pos + 1;
      int upper_start = pos_next + 1;
      int h_upper = sz - pos_next - 1;
      if (h_upper > 0) {
        int v_op_upper = stacks[s][upper_start];
        t = choose_target(s);
        ops.emplace_back(v_op_upper, t + 1);
        vector<int> suffix_upper(stacks[s].begin() + upper_start, stacks[s].end());
        stacks[s].resize(upper_start);
        for (int x : suffix_upper) stacks[t].push_back(x);
      }
      int v_op_lower = stacks[s][lower_start];
      t = choose_target(s);
      ops.emplace_back(v_op_lower, t + 1);
      vector<int> suffix_lower(stacks[s].begin() + lower_start, stacks[s].end());
      stacks[s].resize(lower_start);
      for (int x : suffix_lower) stacks[t].push_back(x);
    }
    ops.emplace_back(current, 0);
    stacks[s].pop_back();
  }
  for (auto [v, i] : ops) {
    cout << v << " " << i << "\n";
  }
  return 0;
}