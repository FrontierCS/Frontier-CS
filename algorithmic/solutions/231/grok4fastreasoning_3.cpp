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
  // Compute topo order using Kahn
  vector<int> order;
  queue<int> q;
  for (int i = 1; i <= n; i++) {
    if (indeg[i] == 0) q.push(i);
  }
  while (!q.empty()) {
    int u = q.front();
    q.pop();
    order.push_back(u);
    for (int v : adj[u]) {
      indeg[v]--;
      if (indeg[v] == 0) q.push(v);
    }
  }
  // Assume DAG, order.size() == n
  assert((int)order.size() == n);
  // Sort adj lists for binary search
  for (int u = 1; u <= n; u++) {
    sort(adj[u].begin(), adj[u].end());
  }
  // Compute missing forward edges in topo order
  vector<tuple<char, int, int>> ops;
  for (size_t i = 0; i < order.size(); i++) {
    for (size_t j = i + 1; j < order.size(); j++) {
      int a = order[i], b = order[j];
      if (!binary_search(adj[a].begin(), adj[a].end(), b)) {
        ops.emplace_back('+', a, b);
      }
    }
  }
  int K = ops.size();
  cout << K << endl;
  for (auto [c, a, b] : ops) {
    cout << "+" << " " << a << " " << b << endl;
  }
  cout.flush();
  // Now g[order[i]] = n - 1 - i
  vector<int> v_by_g(n);
  for (int i = 0; i < n; i++) {
    v_by_g[n - 1 - i] = order[i];
  }
  // Now T rounds
  for (int cas = 0; cas < T; cas++) {
    set<int> possible;
    for (int i = 0; i < n; i++) possible.insert(i);  // g 0 to n-1
    bool found = false;
    while (possible.size() > 1) {
      int tg = *possible.begin();
      int u = v_by_g[tg];
      cout << "? 1 " << u << endl;
      cout.flush();
      string s;
      cin >> s;
      if (s == "Lose") {
        cout << "! " << u << endl;
        cout.flush();
        string res;
        cin >> res;
        if (res == "Wrong") return 0;
        found = true;
        break;
      } else {
        possible.erase(tg);
      }
    }
    if (!found) {
      // size == 1
      int tg = *possible.begin();
      int u = v_by_g[tg];
      cout << "! " << u << endl;
      cout.flush();
      string res;
      cin >> res;
      if (res == "Wrong") return 0;
    }
  }
  return 0;
}