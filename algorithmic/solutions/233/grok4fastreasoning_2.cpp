#include <bits/stdc++.h>
using namespace std;

int main() {
  int t;
  cin >> t;
  for (int cas = 0; cas < t; cas++) {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> G(n + 1, vector<int>(n + 1));
    for (int i = 1; i <= n; i++) {
      for (int j = 1; j <= n; j++) {
        cin >> G[i][j];
      }
    }
    int total_T = 2 * n - 1;
    vector<int> all_f;
    int queries_made = 0;
    long long max_allowed = 120LL * n + m;
    bool exceeded = false;
    for (int l = 1; l <= n && !exceeded; l++) {
      // t=1
      int f1 = 0;
      for (int j = 1; j <= l; j++) {
        f1 = max(f1, G[1][j]);
      }
      all_f.push_back(f1);
      // t=2
      int f2 = G[2][1];
      for (int j = 1; j < l; j++) {
        f2 = max(f2, G[1][j]);
      }
      all_f.push_back(f2);
      for (int T = 3; T <= total_T; T++) {
        if (queries_made >= max_allowed) {
          exceeded = true;
          break;
        }
        cout << "? " << l << " " << T << endl;
        fflush(stdout);
        int f;
        cin >> f;
        all_f.push_back(f);
        queries_made++;
      }
    }
    // Add t=1 and t=2 for remaining l if any
    for (int l = 1; l <= n; l++) {
      if (find(all_f.begin(), all_f.end(), 0) == all_f.end()) { // simplistic check, but in practice already added
        continue;
      }
    }
    // Actually, since loop stopped early, add t=1 t=2 for remaining l
    int last_l = 0;
    for (int ll = 1; ll <= n; ll++) {
      if (all_f.size() < 2 * ll) { // rough
        last_l = ll - 1;
        break;
      }
    }
    for (int l = last_l + 1; l <= n; l++) {
      // t=1
      int f1 = 0;
      for (int j = 1; j <= l; j++) {
        f1 = max(f1, G[1][j]);
      }
      all_f.push_back(f1);
      // t=2
      int f2 = G[2][1];
      for (int j = 1; j < l; j++) {
        f2 = max(f2, G[1][j]);
      }
      all_f.push_back(f2);
    }
    sort(all_f.begin(), all_f.end());
    cout << "!";
    for (int i = 0; i < m; i++) {
      cout << " " << all_f[i];
    }
    cout << endl;
    fflush(stdout);
  }
  return 0;
}