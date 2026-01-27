#include <bits/stdc++.h>
using namespace std;

int satisfied(const vector<vector<int>>& clauses, const vector<int>& assign) {
  int cnt = 0;
  for (const auto& cl : clauses) {
    bool sat = false;
    for (int l : cl) {
      int v = abs(l);
      bool lit = (l > 0) ? (assign[v] == 1) : (assign[v] == 0);
      if (lit) {
        sat = true;
        break;
      }
    }
    if (sat) cnt++;
  }
  return cnt;
}

int get_delta(int v, const vector<int>& assign, const vector<vector<int>>& clauses) {
  int delta = 0;
  for (const auto& cl : clauses) {
    bool sb = false, sa = false;
    for (int l : cl) {
      int vv = abs(l);
      bool cur_lit = (l > 0) ? (assign[vv] == 1) : (assign[vv] == 0);
      bool after_lit = (vv == v) ? !cur_lit : cur_lit;
      sb |= cur_lit;
      sa |= after_lit;
    }
    delta += (sa ? 1 : 0) - (sb ? 1 : 0);
  }
  return delta;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<vector<int>> clauses(m, vector<int>(3));
  for (int i = 0; i < m; i++) {
    for (int j = 0; j < 3; j++) {
      cin >> clauses[i][j];
    }
  }
  if (m == 0) {
    for (int i = 1; i <= n; i++) {
      cout << 0 << (i < n ? " " : "\n");
    }
    return 0;
  }
  srand(time(0));
  vector<int> best_assign(n + 1, 0);
  int best_sat = -1;
  const int RESTARTS = 100;
  for (int r = 0; r < RESTARTS; r++) {
    vector<int> assign(n + 1, 0);
    for (int i = 1; i <= n; i++) assign[i] = rand() % 2;
    int cur_sat = satisfied(clauses, assign);
    while (true) {
      int max_d = 0;
      int flip_v = -1;
      for (int v = 1; v <= n; v++) {
        int d = get_delta(v, assign, clauses);
        if (d > max_d) {
          max_d = d;
          flip_v = v;
        }
      }
      if (max_d <= 0) break;
      assign[flip_v] = 1 - assign[flip_v];
      cur_sat += max_d;
    }
    if (cur_sat > best_sat) {
      best_sat = cur_sat;
      best_assign = assign;
    }
  }
  for (int i = 1; i <= n; i++) {
    cout << best_assign[i] << (i < n ? " " : "\n");
  }
  return 0;
}