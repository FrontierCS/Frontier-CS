#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, M;
  cin >> N >> M;
  vector<vector<int>> adj(N + 1);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  for (int i = 1; i <= N; i++) {
    sort(adj[i].begin(), adj[i].end());
    auto it = unique(adj[i].begin(), adj[i].end());
    adj[i].resize(it - adj[i].begin());
  }
  vector<int> deg(N + 1);
  for (int i = 1; i <= N; i++) deg[i] = adj[i].size();
  vector<pair<int, int>> order;
  for (int i = 1; i <= N; i++) {
    order.emplace_back(-deg[i], i);
  }
  sort(order.begin(), order.end());
  vector<int> coloring(N + 1, 0);
  for (auto& p : order) {
    int v = p.second;
    vector<int> used(N + 1, 0);
    for (int u : adj[v]) {
      int cu = coloring[u];
      if (cu != 0) used[cu] = 1;
    }
    int c = 1;
    while (used[c]) ++c;
    coloring[v] = c;
  }
  for (int i = 1; i <= N; i++) {
    cout << coloring[i] << '\n';
  }
  return 0;
}