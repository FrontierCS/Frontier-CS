#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  if (n == 1) {
    cout << "!" << endl << flush;
    return 0;
  }
  int r = 1;
  vector<vector<bool>> on_path(n + 1, vector<bool>(n + 1, false));
  for (int v = 1; v <= n; ++v) {
    if (v == r) continue;
    on_path[r][v] = true;
    on_path[v][v] = true;
    for (int u = 1; u <= n; ++u) {
      if (u == r || u == v) continue;
      cout << "? 2 " << u << " " << r << " " << v << endl << flush;
      int ans;
      cin >> ans;
      if (ans == -1) return 0;
      on_path[u][v] = (ans == 1);
    }
  }
  set<pair<int, int>> edges;
  for (int v = 1; v <= n; ++v) {
    if (v == r) continue;
    vector<int> chain;
    for (int x = 1; x <= n; ++x) {
      if (on_path[x][v]) chain.push_back(x);
    }
    sort(chain.begin(), chain.end(), [&](int a, int b) {
      return on_path[a][b] && (a != b);
    });
    for (size_t i = 0; i + 1 < chain.size(); ++i) {
      int a = chain[i], b = chain[i + 1];
      if (a > b) swap(a, b);
      edges.insert({a, b});
    }
  }
  cout << "!" << endl << flush;
  for (auto e : edges) {
    cout << e.first << " " << e.second << endl << flush;
  }
  return 0;
}