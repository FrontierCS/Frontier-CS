#include <bits/stdc++.h>
using namespace std;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  vector<vector<char>> adjm(N+1, vector<char>(N+1, 0));
  vector<vector<int>> adj(N+1);
  vector<int> deg(N+1, 0);
  for(int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if(u == v) continue;
    if(!adjm[u][v]) {
      adjm[u][v] = adjm[v][u] = 1;
      adj[u].push_back(v);
      adj[v].push_back(u);
      deg[u]++;
      deg[v]++;
    }
  }
  vector<bool> active(N+1, true);
  vector<int> current_deg = deg;
  vector<int> iset(N+1, 0);
  int remaining = N;
  while(remaining > 0) {
    int min_d = INT_MAX;
    int u = -1;
    for(int i = 1; i <= N; i++) {
      if(active[i] && current_deg[i] < min_d) {
        min_d = current_deg[i];
        u = i;
      }
    }
    if(u == -1) break;
    iset[u] = 1;
    active[u] = false;
    remaining--;
    vector<int> to_remove;
    for(int v : adj[u]) {
      if(active[v]) {
        to_remove.push_back(v);
        active[v] = false;
        remaining--;
      }
    }
    for(int w : adj[u]) {
      if(active[w]) {
        current_deg[w]--;
      }
    }
    for(int v : to_remove) {
      for(int w : adj[v]) {
        if(active[w]) {
          current_deg[w]--;
        }
      }
    }
  }
  for(int i = 1; i <= N; i++) {
    cout << iset[i] << "\n";
  }
  return 0;
}