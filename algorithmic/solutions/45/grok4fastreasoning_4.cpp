#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n, m, k;
  double eps;
  cin >> n >> m >> k >> eps;
  vector<vector<int>> adj(n + 1);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    if (u != v) {
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
  }
  for (int i = 1; i <= n; i++) {
    sort(adj[i].begin(), adj[i].end());
    auto it = unique(adj[i].begin(), adj[i].end());
    adj[i].erase(it, adj[i].end());
  }
  vector<pair<int, int>> nodes;
  for (int i = 1; i <= n; i++) {
    nodes.emplace_back(-(int)adj[i].size(), i);
  }
  sort(nodes.begin(), nodes.end());
  vector<int> order(n);
  for (int i = 0; i < n; i++) {
    order[i] = nodes[i].second;
  }
  int ideal = (n + k - 1) / k;
  double max_d = (1.0 + eps) * ideal;
  int maxs = floor(max_d);
  vector<int> assignment(n + 1, 0);
  vector<int> psize(k + 1, 0);
  for (int idx = 0; idx < n; idx++) {
    int v = order[idx];
    vector<int> cnt(k + 1, 0);
    for (int u : adj[v]) {
      int p = assignment[u];
      if (p != 0) {
        cnt[p]++;
      }
    }
    int best_p = -1;
    int best_c = -1;
    int best_s = INT_MAX;
    bool found = false;
    for (int p = 1; p <= k; p++) {
      if (psize[p] < maxs) {
        int c = cnt[p];
        int s = psize[p];
        if (c > best_c || (c == best_c && s < best_s)) {
          best_c = c;
          best_s = s;
          best_p = p;
        }
        found = true;
      }
    }
    if (!found) {
      best_p = 1;
      best_s = psize[1];
      for (int p = 2; p <= k; p++) {
        if (psize[p] < best_s) {
          best_s = psize[p];
          best_p = p;
        }
      }
    }
    assignment[v] = best_p;
    psize[best_p]++;
  }
  for (int i = 1; i <= n; i++) {
    if (i > 1) cout << " ";
    cout << assignment[i];
  }
  cout << "\n";
  return 0;
}