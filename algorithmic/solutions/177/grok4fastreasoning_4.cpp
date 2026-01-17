#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<vector<int>> adj(n + 1);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  vector<int> color(n + 1, 0);
  vector<pair<int, int>> verts;
  for (int i = 1; i <= n; i++) {
    verts.emplace_back(-adj[i].size(), i);
  }
  sort(verts.begin(), verts.end());
  for (auto& p : verts) {
    int i = p.second;
    bool used[4] = {false};
    int counts[4] = {0};
    for (int nei : adj[i]) {
      int c = color[nei];
      if (c != 0) {
        used[c] = true;
        counts[c]++;
      }
    }
    bool can = false;
    for (int c = 1; c <= 3; c++) {
      if (!used[c]) {
        color[i] = c;
        can = true;
        break;
      }
    }
    if (!can) {
      int minv = INT_MAX;
      int minc = -1;
      for (int c = 1; c <= 3; c++) {
        if (counts[c] < minv) {
          minv = counts[c];
          minc = c;
        }
      }
      color[i] = minc;
    }
  }
  for (int i = 1; i <= n; i++) {
    if (i > 1) cout << " ";
    cout << color[i];
  }
  cout << "\n";
}