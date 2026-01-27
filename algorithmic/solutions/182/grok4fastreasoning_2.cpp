#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  vector<vector<int>> adj(N + 1);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  vector<int> current_deg(N + 1, 0);
  set<pair<int, int>> active;
  for (int i = 1; i <= N; i++) {
    sort(adj[i].begin(), adj[i].end());
    auto it = unique(adj[i].begin(), adj[i].end());
    adj[i].resize(it - adj[i].begin());
    current_deg[i] = adj[i].size();
    if (current_deg[i] > 0) {
      active.insert({-current_deg[i], i});
    }
  }
  vector<int> cover(N + 1, 0);
  while (!active.empty()) {
    auto it = active.begin();
    int v = it->second;
    active.erase(it);
    cover[v] = 1;
    current_deg[v] = 0;
    for (int u : adj[v]) {
      if (current_deg[u] > 0) {
        active.erase({-current_deg[u], u});
        current_deg[u]--;
        if (current_deg[u] > 0) {
          active.insert({-current_deg[u], u});
        }
      }
    }
  }
  for (int i = 1; i <= N; i++) {
    cout << cover[i] << '\n';
  }
  return 0;
}