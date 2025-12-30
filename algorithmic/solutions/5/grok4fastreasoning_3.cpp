#include <bits/stdc++.h>
using namespace std;

int n, m_global;
vector<int> pathh;
vector<char> visitedd;

bool dfs_forward(int u, const vector<vector<int>>& adj) {
  visitedd[u] = 1;
  pathh.push_back(u);
  if ((int)pathh.size() == n) return true;
  vector<pair<int, int>> cands;
  for (int v : adj[u]) {
    if (!visitedd[v]) {
      int cnt = 0;
      for (int w : adj[v]) {
        if (!visitedd[w]) ++cnt;
      }
      cands.emplace_back(cnt, v);
    }
  }
  sort(cands.begin(), cands.end());
  for (auto& p : cands) {
    if (dfs_forward(p.second, adj)) return true;
  }
  pathh.pop_back();
  visitedd[u] = 0;
  return false;
}

bool dfs_backward(int u, const vector<vector<int>>& back_adj) {
  visitedd[u] = 1;
  pathh.push_back(u);
  if ((int)pathh.size() == n) return true;
  vector<pair<int, int>> cands;
  for (int v : back_adj[u]) {
    if (!visitedd[v]) {
      int cnt = 0;
      for (int w : back_adj[v]) {
        if (!visitedd[w]) ++cnt;
      }
      cands.emplace_back(cnt, v);
    }
  }
  sort(cands.begin(), cands.end());
  for (auto& p : cands) {
    if (dfs_backward(p.second, back_adj)) return true;
  }
  pathh.pop_back();
  visitedd[u] = 0;
  return false;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  cin >> n >> m_global;
  vector<int> dummy(10);
  for (int &x : dummy) cin >> x;
  vector<vector<int>> adj(n + 1);
  vector<int> indeg(n + 1, 0), outdeg(n + 1, 0);
  for (int i = 0; i < m_global; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    indeg[v]++;
    outdeg[u]++;
  }
  int source = -1;
  for (int i = 1; i <= n; i++) {
    if (indeg[i] == 0) {
      source = i;
      break;
    }
  }
  int sinkk = -1;
  for (int i = 1; i <= n; i++) {
    if (outdeg[i] == 0) {
      sinkk = i;
      break;
    }
  }
  visitedd.assign(n + 1, 0);
  bool foundd = false;
  pathh.clear();
  if (source != -1) {
    foundd = dfs_forward(source, adj);
  } else if (sinkk != -1) {
    vector<vector<int>> back_adj(n + 1);
    for (int u = 1; u <= n; u++) {
      for (int v : adj[u]) {
        back_adj[v].push_back(u);
      }
    }
    foundd = dfs_backward(sinkk, back_adj);
    if (foundd) {
      reverse(pathh.begin(), pathh.end());
    }
  } else {
    int max_od = -1;
    int st = -1;
    for (int i = 1; i <= n; i++) {
      if (outdeg[i] > max_od || (outdeg[i] == max_od && (st == -1 || i < st))) {
        max_od = outdeg[i];
        st = i;
      }
    }
    if (st != -1) {
      foundd = dfs_forward(st, adj);
    }
  }
  if (pathh.empty()) {
    cout << 1 << '\n' << 1 << '\n';
  } else {
    cout << pathh.size() << '\n';
    for (size_t j = 0; j < pathh.size(); j++) {
      if (j > 0) cout << " ";
      cout << pathh[j];
    }
    cout << '\n';
  }
  return 0;
}