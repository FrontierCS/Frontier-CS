#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> stacks(m);
  int sz = n / m;
  for (int i = 0; i < m; i++) {
    stacks[i].resize(sz);
    for (int j = 0; j < sz; j++) {
      cin >> stacks[i][j];
    }
  }
  vector<pair<int, int>> ops;
  int current_v = 1;
  while (current_v <= n) {
    int s = -1, pos = -1;
    bool found = false;
    for (int i = 0; i < m; i++) {
      for (int j = 0; j < (int)stacks[i].size(); j++) {
        if (stacks[i][j] == current_v) {
          s = i;
          pos = j;
          found = true;
          break;
        }
      }
      if (found) break;
    }
    int ssize = stacks[s].size();
    if (pos != ssize - 1) {
      int move_v = stacks[s][pos + 1];
      int best_d = -1;
      for (int d = 0; d < m; d++) {
        if (d != s && stacks[d].empty()) {
          best_d = d;
          break;
        }
      }
      if (best_d == -1) {
        int best_score = -1;
        for (int d = 0; d < m; d++) {
          if (d == s) continue;
          if (stacks[d].empty()) continue;
          int topv = stacks[d].back();
          if (topv > best_score) {
            best_score = topv;
            best_d = d;
          }
        }
      }
      vector<int> suffix;
      for (int j = pos + 1; j < ssize; j++) {
        suffix.push_back(stacks[s][j]);
      }
      ops.push_back({move_v, best_d + 1});
      stacks[s].resize(pos + 1);
      for (int x : suffix) {
        stacks[best_d].push_back(x);
      }
    }
    ops.push_back({current_v, 0});
    stacks[s].pop_back();
    current_v++;
  }
  for (auto p : ops) {
    cout << p.first << " " << p.second << "\n";
  }
  return 0;
}