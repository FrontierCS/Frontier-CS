#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<int> a(10);
  for (int i = 0; i < 10; i++) cin >> a[i];
  vector<vector<int>> adj(n + 1);
  vector<int> indeg(n + 1, 0);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    indeg[v]++;
  }
  vector<pair<int, int>> candidates;
  for (int i = 1; i <= n; i++) {
    candidates.emplace_back(indeg[i], i);
  }
  sort(candidates.begin(), candidates.end());
  vector<int> path;
  path.reserve(n);
  vector<int> vis_time(n + 1, 0);
  int timestamp = 0;
  vector<int> best_path;
  int best_k = 0;
  auto dfs = [&](auto&& self, int u, int cur_time) -> bool {
    path.push_back(u);
    vis_time[u] = cur_time;
    bool res = false;
    if (path.size() == static_cast<size_t>(n)) {
      res = true;
    } else {
      for (int v : adj[u]) {
        if (vis_time[v] != cur_time) {
          if (self(self, v, cur_time)) {
            res = true;
            break;
          }
        }
      }
    }
    if (!res) {
      if (static_cast<int>(path.size()) > best_k) {
        best_k = path.size();
        best_path = path;
      }
      path.pop_back();
      vis_time[u] = 0;
      return false;
    } else {
      return true;
    }
  };
  bool found_ham = false;
  for (auto& p : candidates) {
    int start = p.second;
    timestamp++;
    path.clear();
    if (dfs(dfs, start, timestamp)) {
      best_path = path;
      best_k = n;
      found_ham = true;
      break;
    }
  }
  if (best_k == 0) {
    cout << 1 << '\n' << 1 << '\n';
  } else {
    cout << best_k << '\n';
    for (int i = 0; i < best_k; i++) {
      if (i > 0) cout << " ";
      cout << best_path[i];
    }
    cout << '\n';
  }
}