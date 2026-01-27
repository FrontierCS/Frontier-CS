#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<array<int, 2>> clauses(m);
  vector<vector<int>> var_clauses(n + 1);
  for (int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    clauses[i][0] = a;
    clauses[i][1] = b;
    var_clauses[abs(a)].push_back(i);
    var_clauses[abs(b)].push_back(i);
  }
  vector<int> assignment(n + 1, 0);
  vector<bool> clause_sat(m, false);
  int num_sat = 0;
  auto lit_sat = [&](int lit, int flipv = -1, int flipval = -1) -> bool {
    int v = abs(lit);
    int val = (v == flipv ? flipval : assignment[v]);
    int des = (lit > 0 ? 1 : 0);
    return val == des;
  };
  for (int i = 0; i < m; i++) {
    bool s = lit_sat(clauses[i][0]) || lit_sat(clauses[i][1]);
    clause_sat[i] = s;
    if (s) num_sat++;
  }
  bool changed = true;
  while (changed) {
    changed = false;
    for (int x = 1; x <= n; x++) {
      int oldv = assignment[x];
      int newv = 1 - oldv;
      int delta = 0;
      for (int ci : var_clauses[x]) {
        bool olds = clause_sat[ci];
        bool news = lit_sat(clauses[ci][0], x, newv) || lit_sat(clauses[ci][1], x, newv);
        if (olds != news) {
          delta += news ? 1 : -1;
        }
      }
      if (delta > 0) {
        assignment[x] = newv;
        num_sat += delta;
        for (int ci : var_clauses[x]) {
          bool news = lit_sat(clauses[ci][0]) || lit_sat(clauses[ci][1]);
          clause_sat[ci] = news;
        }
        changed = true;
      }
    }
  }
  for (int i = 1; i <= n; i++) {
    cout << assignment[i];
    if (i < n) cout << " ";
    else cout << "\n";
  }
  return 0;
}