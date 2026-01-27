#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  bitset<1001> adj[1001];
  vector<int> deg(N + 1, 0);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if (u == v) continue;
    if (!adj[u][v]) {
      adj[u][v] = 1;
      adj[v][u] = 1;
      deg[u]++;
      deg[v]++;
    }
  }
  vector<pair<int, int>> ord;
  for (int i = 1; i <= N; i++) {
    ord.emplace_back(-deg[i], i);
  }
  sort(ord.begin(), ord.end());
  vector<int> verts;
  for (auto p : ord) verts.push_back(p.second);
  vector<int> clique;
  for (int u : verts) {
    bool ok = true;
    for (int v : clique) {
      if (!adj[u][v]) {
        ok = false;
        break;
      }
    }
    if (ok) {
      clique.push_back(u);
    }
  }
  vector<int> res(N + 1, 0);
  for (int u : clique) res[u] = 1;
  for (int i = 1; i <= N; i++) {
    cout << res[i] << '\n';
  }
  return 0;
}