#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m, T;
  cin >> n >> m >> T;
  vector<vector<int>> adj(n + 1);
  vector<vector<bool>> exist(n + 1, vector<bool>(n + 1, false));
  vector<int> indeg(n + 1, 0);
  for (int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    adj[a].push_back(b);
    exist[a][b] = true;
    indeg[b]++;
  }
  // topo sort using Kahn
  queue<int> q;
  for (int i = 1; i <= n; i++)
    if (indeg[i] == 0) q.push(i);
  vector<int> order;
  while (!q.empty()) {
    int u = q.front();
    q.pop();
    order.push_back(u);
    for (int v : adj[u]) {
      indeg[v]--;
      if (indeg[v] == 0) q.push(v);
    }
  }
  if (order.size() != (size_t)n) {
    // cycle, but guaranteed no
    assert(false);
  }
  // now order[0] source, order[n-1] sink
  // g[order[i]] = n-1 - i;
  // find missing edges
  vector<pair<int, int>> adds;
  for (int i = 0; i < n; i++) {
    for (int j = i + 1; j < n; j++) {
      int u = order[i], v = order[j];
      if (!exist[u][v]) {
        adds.emplace_back(u, v);
      }
    }
  }
  int K = adds.size();
  cout << K << endl;
  for (auto [a, b] : adds) {
    cout << "+ " << a << " " << b << endl;
  }
  cout.flush();
  // now T rounds
  for (int t = 0; t < T; t++) {
    set<int> poss;
    for (int i = 1; i <= n; i++) poss.insert(i);
    bool found = false;
    while (poss.size() > 1 && !found) {
      int u = *poss.begin();
      cout << "? 1 " << u << endl;
      cout.flush();
      string res;
      cin >> res;
      if (res == "Lose") {
        cout << "! " << u << endl;
        cout.flush();
        string ver;
        cin >> ver;
        if (ver == "Wrong") return 0;
        found = true;
      } else {
        poss.erase(u);
      }
    }
    if (!found && poss.size() == 1) {
      int u = *poss.begin();
      cout << "! " << u << endl;
      cout.flush();
      string ver;
      cin >> ver;
      if (ver == "Wrong") return 0;
    }
  }
  return 0;
}