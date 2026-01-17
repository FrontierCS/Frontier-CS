#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> current(n + 2);
  for (int i = 1; i <= n; i++) {
    current[i].resize(m);
    for (int j = 0; j < m; j++) {
      cin >> current[i][j];
    }
  }
  vector<int> target(n + 1);
  for (int c = 1; c <= n; c++) target[c] = c;
  vector<pair<int, int>> moves;
  int aux = n + 1;
  bool done = false;
  while (!done && (int)moves.size() < 10000010) {
    done = true;
    for (int c = 1; c <= n; c++) {
      int t = target[c];
      if ((int)current[t].size() != m) {
        done = false;
        break;
      }
      bool all_good = true;
      for (int b : current[t]) {
        if (b != c) {
          all_good = false;
          break;
        }
      }
      if (!all_good) {
        done = false;
        break;
      }
    }
    if (done) break;
    bool moved = false;
    // First priority: move exposed correct ball to its target
    for (int c = 1; c <= n && !moved; c++) {
      int t = target[c];
      if ((int)current[t].size() == m) continue;
      for (int p = 1; p <= n + 1 && !moved; p++) {
        if (p == t) continue;
        if (!current[p].empty() && current[p].back() == c &&
            (int)current[t].size() <= m - 1) {
          current[t].push_back(current[p].back());
          current[p].pop_back();
          moves.emplace_back(p, t);
          moved = true;
        }
      }
    }
    // Second priority: move to aux to expose a correct ball
    if (!moved && (int)current[aux].size() <= m - 1) {
      bool found_excavate = false;
      for (int p = 1; p <= n + 1 && !found_excavate; p++) {
        if (p == aux) continue;
        size_t sz = current[p].size();
        if (sz >= 2) {
          int second = current[p][sz - 2];
          int tt = target[second];
          if ((int)current[tt].size() < m) {
            current[aux].push_back(current[p].back());
            current[p].pop_back();
            moves.emplace_back(p, aux);
            moved = true;
            found_excavate = true;
          }
        }
      }
      if (!found_excavate) {
        // move any
        for (int p = 1; p <= n + 1 && !moved; p++) {
          if (p == aux) continue;
          if (!current[p].empty()) {
            current[aux].push_back(current[p].back());
            current[p].pop_back();
            moves.emplace_back(p, aux);
            moved = true;
          }
        }
      }
    }
    // Third: move from aux to some available pillar
    if (!moved && !current[aux].empty()) {
      for (int p = 1; p <= n + 1 && !moved; p++) {
        if (p == aux) continue;
        if ((int)current[p].size() <= m - 1) {
          current[p].push_back(current[aux].back());
          current[aux].pop_back();
          moves.emplace_back(aux, p);
          moved = true;
        }
      }
    }
    if (!moved) {
      // Should not happen
      assert(false);
    }
  }
  if (!done) {
    // Error, but assume it finishes
    cout << 0 << endl;
    return 0;
  }
  cout << moves.size() << endl;
  for (auto [x, y] : moves) {
    cout << x << " " << y << endl;
  }
  return 0;
}