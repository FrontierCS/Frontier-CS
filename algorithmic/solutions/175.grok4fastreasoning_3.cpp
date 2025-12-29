#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  srand(time(0));
  int n, m;
  cin >> n >> m;
  vector<array<int, 3>> clauses(m);
  vector<vector<pair<int, bool>>> var_occ(n);
  for (int i = 0; i < m; i++) {
    int a, b, c;
    cin >> a >> b >> c;
    clauses[i] = {a, b, c};
    for (int lit : {a, b, c}) {
      if (lit != 0) {
        int v = abs(lit) - 1;
        bool pos = lit > 0;
        var_occ[v].emplace_back(i, pos);
      }
    }
  }
  vector<char> assign(n);
  vector<char> best_assign(n);
  vector<int> num_true(m);
  vector<int> unsat_list;
  vector<int> pos_in_list(m);
  int best_unsat = INT_MAX;
  const int num_restarts = 3;
  const long long max_steps_per_restart = 100000LL;
  for (int r = 0; r < num_restarts; r++) {
    for (int i = 0; i < n; i++) assign[i] = rand() % 2;
    for (int j = 0; j < m; j++) {
      num_true[j] = 0;
      auto& cl = clauses[j];
      for (int k = 0; k < 3; k++) {
        int lit = cl[k];
        int v = abs(lit) - 1;
        bool pos = lit > 0;
        bool val = assign[v] != 0;
        bool litval = pos ? val : !val;
        if (litval) num_true[j]++;
      }
    }
    unsat_list.clear();
    fill(pos_in_list.begin(), pos_in_list.end(), -1);
    for (int j = 0; j < m; j++) {
      if (num_true[j] == 0) {
        pos_in_list[j] = unsat_list.size();
        unsat_list.push_back(j);
      }
    }
    int curr_unsat = unsat_list.size();
    if (curr_unsat < best_unsat) {
      best_unsat = curr_unsat;
      best_assign = assign;
    }
    long long steps = 0;
    while (!unsat_list.empty() && steps < max_steps_per_restart) {
      size_t sz = unsat_list.size();
      int idx = rand() % sz;
      int j = unsat_list[idx];
      vector<int> false_vs;
      auto& cl = clauses[j];
      for (int k = 0; k < 3; k++) {
        int lit = cl[k];
        int v = abs(lit) - 1;
        bool pos = lit > 0;
        bool val = assign[v] != 0;
        bool litval = pos ? val : !val;
        if (!litval) {
          false_vs.push_back(v);
        }
      }
      if (false_vs.empty()) {
        int p = pos_in_list[j];
        if (p != -1) {
          int last = unsat_list.back();
          unsat_list[p] = last;
          pos_in_list[last] = p;
          unsat_list.pop_back();
          pos_in_list[j] = -1;
        }
        steps++;
        continue;
      }
      int v = false_vs[rand() % false_vs.size()];
      char old_val_c = assign[v];
      bool old_v = old_val_c != 0;
      for (auto& p : var_occ[v]) {
        int j2 = p.first;
        bool pos2 = p.second;
        bool old_litval = pos2 ? old_v : !old_v;
        int delta_num = old_litval ? -1 : 1;
        int old_num = num_true[j2];
        int new_num = old_num + delta_num;
        num_true[j2] = new_num;
        bool old_uns = (old_num == 0);
        bool new_uns = (new_num == 0);
        if (old_uns != new_uns) {
          if (new_uns) {
            if (pos_in_list[j2] == -1) {
              pos_in_list[j2] = unsat_list.size();
              unsat_list.push_back(j2);
            }
          } else {
            int p2 = pos_in_list[j2];
            if (p2 != -1) {
              int last = unsat_list.back();
              unsat_list[p2] = last;
              pos_in_list[last] = p2;
              unsat_list.pop_back();
              pos_in_list[j2] = -1;
            }
          }
        }
      }
      assign[v] = 1 - old_val_c;
      steps++;
    }
    curr_unsat = unsat_list.size();
    if (curr_unsat < best_unsat) {
      best_unsat = curr_unsat;
      best_assign = assign;
    }
  }
  for (int i = 0; i < n; i++) {
    cout << (int)best_assign[i];
    if (i + 1 < n) cout << " ";
    else cout << "\n";
  }
  return 0;
}