#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m, T;
  cin >> n >> m >> T;
  vector<vector<int>> adj(n + 1);
  vector<int> indeg(n + 1, 0);
  for (int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    adj[a].push_back(b);
    indeg[b]++;
  }
  // Kahn's algorithm for topo sort (sources first)
  queue<int> q;
  for (int u = 1; u <= n; u++) {
    if (indeg[u] == 0) q.push(u);
  }
  vector<int> topo;
  while (!q.empty()) {
    int u = q.front(); q.pop();
    topo.push_back(u);
    for (int v : adj[u]) {
      if (--indeg[v] == 0) q.push(v);
    }
  }
  reverse(topo.begin(), topo.end()); // now sinks first for grundy computation
  vector<int> g(n + 1, -1);
  for (int i = 0; i < n; i++) {
    int u = topo[i];
    set<int> s;
    for (int v : adj[u]) s.insert(g[v]);
    int mex = 0;
    while (s.count(mex)) mex++;
    g[u] = mex;
  }
  // Output K = 0
  cout << 0 << endl;
  cout.flush();
  // For each test case
  for (int test = 0; test < T; test++) {
    vector<int> possible;
    for (int u = 1; u <= n; u++) possible.push_back(u);
    while (possible.size() > 1) {
      int u = possible[0]; // Test the first in possible
      cout << "? 1 " << u << endl;
      cout.flush();
      string ans;
      cin >> ans;
      if (ans == "Lose") {
        possible = {u};
      } else {
        vector<int> newp;
        for (int v : possible) {
          if (v != u) newp.push_back(v);
        }
        possible = newp;
      }
    }
    int v = possible[0];
    cout << "! " << v << endl;
    cout.flush();
    string verdict;
    cin >> verdict;
    if (verdict == "Wrong") {
      return 0;
    }
  }
  return 0;
}