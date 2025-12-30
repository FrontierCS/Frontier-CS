#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> adj;
vector<int> outdeg, indeg;
vector<char> visited;
vector<int> path;

bool dfs(int u, int count) {
  path.push_back(u);
  visited[u] = 1;
  if (count == n) return true;
  for (int v : adj[u]) {
    if (!visited[v]) {
      if (dfs(v, count + 1)) return true;
    }
  }
  path.pop_back();
  visited[u] = 0;
  return false;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  cin >> n >> m;
  for (int i = 0; i < 10; i++) {
    int x;
    cin >> x;
  }
  adj.assign(n + 1, {});
  indeg.assign(n + 1, 0);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    indeg[v]++;
  }
  outdeg.assign(n + 1, 0);
  for (int i = 1; i <= n; i++) {
    outdeg[i] = adj[i].size();
  }
  for (int i = 1; i <= n; i++) {
    sort(adj[i].begin(), adj[i].end(), [&](int a, int b) {
      return outdeg[a] < outdeg[b];
    });
  }
  int min_ind = INT_MAX;
  for (int i = 1; i <= n; i++) {
    min_ind = min(min_ind, indeg[i]);
  }
  vector<int> candidates;
  for (int i = 1; i <= n; i++) {
    if (indeg[i] == min_ind) candidates.push_back(i);
  }
  sort(candidates.begin(), candidates.end(), [&](int a, int b) {
    if (outdeg[a] != outdeg[b]) return outdeg[a] < outdeg[b];
    return a < b;
  });
  bool found = false;
  visited.assign(n + 1, 0);
  path.reserve(n);
  for (int st : candidates) {
    fill(visited.begin(), visited.end(), 0);
    path.clear();
    if (dfs(st, 1)) {
      found = true;
      break;
    }
  }
  if (found && (int)path.size() == n) {
    cout << n << '\n';
    for (size_t i = 0; i < path.size(); i++) {
      if (i) cout << " ";
      cout << path[i];
    }
    cout << '\n';
  } else {
    cout << 1 << '\n';
    cout << 1 << '\n';
  }
  return 0;
}