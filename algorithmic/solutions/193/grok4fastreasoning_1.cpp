#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<pair<int, int>> clauses(m);
  for (int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    clauses[i] = {a, b};
  }
  vector<vector<int>> var_clauses(n);
  for (int j = 0; j < m; j++) {
    int a = clauses[j].first, b = clauses[j].second;
    int va = abs(a) - 1, vb = abs(b) - 1;
    var_clauses[va].push_back(j);
    if (va != vb) var_clauses[vb].push_back(j);
  }
  srand(time(NULL));
  vector<int> best_assign(n, 0);
  int best_satisfied = -1;
  const int TRIALS = 10;
  for (int trial = 0; trial < TRIALS; trial++) {
    vector<int> assign(n);
    for (int i = 0; i < n; i++) assign[i] = rand() % 2;
    int satisfied = 0;
    for (int j = 0; j < m; j++) {
      int a = clauses[j].first, b = clauses[j].second;
      int va = abs(a) - 1, vb = abs(b) - 1;
      bool la = (a > 0 ? assign[va] == 1 : assign[va] == 0);
      bool lb = (b > 0 ? assign[vb] == 1 : assign[vb] == 0);
      if (la || lb) satisfied++;
    }
    bool changed = true;
    while (changed) {
      changed = false;
      vector<int> delta(n, 0);
      for (int v = 0; v < n; v++) {
        int d = 0;
        for (int j : var_clauses[v]) {
          int a = clauses[j].first, b = clauses[j].second;
          int va = abs(a) - 1, vb = abs(b) - 1;
          bool la_curr = (a > 0 ? assign[va] == 1 : assign[va] == 0);
          bool lb_curr = (b > 0 ? assign[vb] == 1 : assign[vb] == 0);
          bool curr_sat = la_curr || lb_curr;
          bool la_after = la_curr;
          if (va == v) la_after = !la_curr;
          bool lb_after = lb_curr;
          if (vb == v) lb_after = !lb_curr;
          bool after_sat = la_after || lb_after;
          if (after_sat && !curr_sat) d++;
          if (!after_sat && curr_sat) d--;
        }
        delta[v] = d;
      }
      int maxd = 0;
      int bestv = -1;
      for (int v = 0; v < n; v++) {
        if (delta[v] > maxd) {
          maxd = delta[v];
          bestv = v;
        }
      }
      if (maxd > 0) {
        assign[bestv] = 1 - assign[bestv];
        satisfied += maxd;
        changed = true;
      }
    }
    if (satisfied > best_satisfied) {
      best_satisfied = satisfied;
      best_assign = assign;
    }
  }
  for (int i = 0; i < n; i++) {
    cout << best_assign[i];
    if (i < n - 1) cout << " ";
    else cout << "\n";
  }
  return 0;
}