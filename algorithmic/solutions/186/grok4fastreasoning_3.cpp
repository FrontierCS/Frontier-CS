#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  set<pair<int, int>> edge_set;
  vector<vector<int>> adj(N + 1);
  vector<int> deg(N + 1, 0);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if (u > v) swap(u, v);
    if (edge_set.count({u, v})) continue;
    edge_set.insert({u, v});
    adj[u].push_back(v);
    adj[v].push_back(u);
    deg[u]++;
    deg[v]++;
  }
  vector<pair<int, int>> order;
  for (int i = 1; i <= N; i++) {
    order.emplace_back(-deg[i], i);
  }
  sort(order.begin(), order.end());
  vector<int> color(N + 1, 0);
  for (auto& p : order) {
    int v = p.second;
    vector<char> used(N + 2, 0);
    for (int nei : adj[v]) {
      int c = color[nei];
      if (c != 0) {
        used[c] = 1;
      }
    }
    int c = 1;
    while (used[c]) c++;
    color[v] = c;
  }
  for (int i = 1; i <= N; i++) {
    cout << color[i] << '\n';
  }
  return 0;
}