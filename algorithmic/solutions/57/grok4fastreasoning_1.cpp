#include <bits/stdc++.h>
using namespace std;

void dfs(int node, int p, const vector<long long>& f, vector<int>& val, vector<int>& sz, const vector<vector<int>>& adj) {
  if (p == -1) {
    val[node] = (int)f[node];
  } else {
    val[node] = (int)(f[node] - f[p]);
  }
  sz[node] = 1;
  for (int c : adj[node]) {
    if (c != p) {
      dfs(c, node, f, val, sz, adj);
      sz[node] += sz[c];
    }
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int tt = 0; tt < t; ++tt) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    vector<long long> f(n + 1);
    for (int u = 1; u <= n; ++u) {
      cout << "? 1 1 " << u << endl;
      cout.flush();
      cin >> f[u];
    }
    vector<int> candidates;
    for (int r = 1; r <= n; ++r) {
      if (abs(f[r]) == 1) {
        candidates.push_back(r);
      }
    }
    int nc = candidates.size();
    vector<vector<int>> all_vals(nc, vector<int>(n + 1));
    for (int i = 0; i < nc; ++i) {
      int r = candidates[i];
      vector<int> val(n + 1), sz(n + 1);
      dfs(r, -1, f, val, sz, adj);
      all_vals[i] = val;
    }
    vector<int> active(nc);
    for (int i = 0; i < nc; ++i) active[i] = i;
    set<int> toggled;
    while (active.size() > 1) {
      int best_m = -1;
      int min_maxg = INT_MAX;
      bool can_split = false;
      for (int mm = 1; mm <= n; ++mm) {
        map<int, int> cnt;
        for (int j : active) {
          int vv = all_vals[j][mm];
          cnt[vv]++;
        }
        if (cnt.size() > 1) {
          int maxg = 0;
          for (auto& pr : cnt) maxg = max(maxg, pr.second);
          if (maxg < min_maxg) {
            min_maxg = maxg;
            best_m = mm;
            can_split = true;
          }
        }
      }
      if (!can_split) {
        active = {active[0]};
        break;
      }
      int m = best_m;
      cout << "? 1 1 " << m << endl;
      cout.flush();
      long long current_fm;
      cin >> current_fm;
      cout << "? 2 " << m << endl;
      cout.flush();
      cout << "? 1 1 " << m << endl;
      cout.flush();
      long long new_fm;
      cin >> new_fm;
      long long delta = new_fm - current_fm;
      int learned_v = -static_cast<int>(delta / 2);
      vector<int> new_active;
      for (int j : active) {
        if (all_vals[j][m] == learned_v) {
          new_active.push_back(j);
        }
      }
      active = new_active;
      toggled.insert(m);
    }
    int true_i = active[0];
    vector<int> initial_v = all_vals[true_i];
    vector<int> final_v(n + 1);
    for (int i = 1; i <= n; ++i) {
      final_v[i] = initial_v[i];
    }
    for (int ttog : toggled) {
      final_v[ttog] = -final_v[ttog];
    }
    cout << "!";
    for (int i = 1; i <= n; ++i) {
      cout << " " << final_v[i];
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}