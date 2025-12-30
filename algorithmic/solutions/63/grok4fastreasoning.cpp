#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  vector<vector<int>> adj(N);
  vector<pair<int, int>> edges(M);
  map<pair<int, int>, int> edge_id;
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if (u > v) swap(u, v);
    edges[i] = {u, v};
    edge_id[{u, v}] = i;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  // Find bridges
  vector<int> disc(N, -1), low(N, -1);
  int time_stamp = 0;
  set<pair<int, int>> bridges;
  function<void(int, int)> find_bridges = [&](int u