#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  bitset<501> adj[501];
  int deg[501] = {0};
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if (!adj[u][v]) {
      adj[u][v] = 1;
      adj[v][u] = 1;
      deg[u]++;
      deg[v]++;
    }
  }
  vector<int> verts(N);
  for (int i = 0; i < N; i++) verts[i] = i + 1;
  sort(verts.begin(), verts.end(), [&](int a, int b) {
    return (N - 1 - deg[a]) > (N - 1 - deg[b]);
  });
  vector<int> color(N + 1, 0);
  for (int i = 0; i < N; i++) {
    int u = verts[i];
    vector<char> forbidden(N + 1, 0);
    for (int j = 0; j < i; j++) {
      int v = verts[j];
      if (!adj[u][v]) {
        forbidden[color[v]] = 1;
      }
    }
    int c = 1;
    while (forbidden[c]) c++;
    color[u] = c;
  }
  for (int i = 1; i <= N; i++) {
    cout << color[i] << '\n';
  }
  return 0;
}