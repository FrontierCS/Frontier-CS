#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  bitset<501> adj[501];
  for(int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    adj[u][v] = 1;
    adj[v][u] = 1;
  }
  vector<vector<int>> adjlist(N+1);
  for(int u = 1; u <= N; u++) {
    for(int v = 1; v <= N; v++) {
      if(adj[u][v]) {
        adjlist[u].push_back(v);
      }
    }
  }
  vector<int> deg(N+1);
  for(int u = 1; u <= N; u++) {
    deg[u] = adjlist[u].size();
  }
  vector<int> color(N+1, 0);
  vector<bitset<501>> usedcolors(N+1);
  vector<int> saturation(N+1, 0);
  vector<int> uncolored;
  for(int i = 1; i <= N; i++) uncolored.push_back(i);
  while(!uncolored.empty()) {
    int best = N+1;
    int msat = -1;
    int mdeg = -1;
    for(int cand : uncolored) {
      int s = saturation[cand];
      int d = deg[cand];
      if(s > msat ||
         (s == msat && d > mdeg) ||
         (s == msat && d == mdeg && cand < best)) {
        msat = s;
        mdeg = d;
        best = cand;
      }
    }
    auto it = find(uncolored.begin(), uncolored.end(), best);
    uncolored.erase(it);
    vector<char> forbidden(N+2, 0);
    for(int v : adjlist[best]) {
      int cv = color[v];
      if(cv != 0) {
        forbidden[cv] = 1;
      }
    }
    int c = 1;
    while(forbidden[c]) ++c;
    color[best] = c;
    for(int w : adjlist[best]) {
      if(color[w] == 0) {
        if(!usedcolors[w][c]) {
          usedcolors[w][c] = 1;
          ++saturation[w];
        }
      }
    }
  }
  for(int i = 1; i <= N; i++) {
    cout << color[i] << '\n';
  }
  return 0;
}