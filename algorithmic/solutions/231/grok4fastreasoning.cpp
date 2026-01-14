#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n, m, T;
  cin >> n >> m >> T;
  vector<vector<int>> adj(n + 1);
  vector<vector<bool>> has(n + 1, vector<bool>(n + 1, false));
  vector<int> in_deg(n + 1, 0);
  for (int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    adj[a].push_back(b);
    has[a][b] = true;
    in_deg[b]++;
  }
  // Kahn's algorithm for topo order (sources first)
  queue<int> q;
  for (int i = 1; i <= n; i++) {
    if (in_deg[i] == 0) q.push(i);
  }
  vector<int> topo;
  vector<int> temp_deg = in_deg;
  while (!q.empty()) {
    int u = q.front();
    q.pop();
    topo.push_back(u);
    for (int v : adj[u]) {
      temp_deg[v]--;
      if (temp_deg[v] == 0) q.push(v);
    }
  }
  if (topo.size() != (size_t)n) {
    // Should not happen, DAG guaranteed
    assert(false);
  }
  // Count additions for complete DAG
  vector<pair<int, int>> adds;
  for (int i = 0; i < n; i++) {
    int a = topo[i];
    for (int j = i + 1; j < n; j++) {
      int b = topo[j];
      if (!has[a][b]) {
        adds.emplace_back(a, b);
      }
    }
  }
  int K = adds.size();
  cout << K << endl;
  cout.flush();
  for (auto [a, b] : adds) {
    cout << "+ " << a << " " << b << endl;
    cout.flush();
  }
  // Compute grundy: g[topo[i]] = n - 1 - i
  vector<int> grundy(n + 1, 0);
  for (int i = 0; i < n; i++) {
    int u = topo[i];
    grundy[u] = n - 1 - i;
  }
  // Now T rounds
  for (int tc = 0; tc < T; tc++) {
    set<int> poss;
    for (int i = 1; i <= n; i++) poss.insert(i);
    bool done = false;
    while (poss.size() > 1 && !done) {
      auto it = poss.begin();
      int testv = *it;
      poss.erase(it);
      cout << "? 1 " << testv << endl;
      cout.flush();
      string ans;
      cin >> ans;
      if (ans == "Lose") {
        cout << "! " << testv << endl;
        cout.flush();
        string ver;
        cin >> ver;
        if (ver == "Wrong") {
          return 0;
        }
        done = true;
      }
      // else Win, poss already reduced, continue
    }
    if (!done && poss.size() == 1) {
      int v = *poss.begin();
      cout << "! " << v << endl;
      cout.flush();
      string ver;
      cin >> ver;
      if (ver == "Wrong") {
        return 0;
      }
    }
  }
  return 0;
}