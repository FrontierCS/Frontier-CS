#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<int> S(n), Targ(n);
  for (int &x : S) cin >> x;
  for (int &x : Targ) cin >> x;
  vector<vector<int>> adj(n + 1);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  // dist0, par0
  vector<int> dist0(n + 1, -1);
  vector<int> par0(n + 1, -1);
  queue<int> q;
  for (int i = 1; i <= n; i++) {
    if (S[i - 1] == 0) {
      dist0[i] = 0;
      q.push(i);
    }
  }
  while (!q.empty()) {
    int u = q.front();
    q.pop();
    for (int v : adj[u]) {
      if (dist0[v] == -1) {
        dist0[v] = dist0[u] + 1;
        par0[v] = u;
        q.push(v);
      }
    }
  }
  // dist1, par1
  vector<int> dist1(n + 1, -1);
  vector<int> par1(n + 1, -1);
  while (!q.empty()) q.pop();
  for (int i = 1; i <= n; i++) {
    if (S[i - 1] == 1) {
      dist1[i] = 0;
      q.push(i);
    }
  }
  while (!q.empty()) {
    int u = q.front();
    q.pop();
    for (int v : adj[u]) {
      if (dist1[v] == -1) {
        dist1[v] = dist1[u] + 1;
        par1[v] = u;
        q.push(v);
      }
    }
  }
  // compute lb
  int lb = 0;
  for (int i = 1; i <= n; i++) {
    if (S[i - 1] == Targ[i - 1]) continue;
    int cc = Targ[i - 1];
    int d = (cc == 0 ? dist0[i] : dist1[i]);
    lb = max(lb, d);
  }
  // req
  vector<int> req_t(n + 1, 0);
  vector<int> req_c(n + 1, -1);
  vector<int> req_par(n + 1, -1);
  for (int i = 1; i <= n; i++) {
    if (S[i - 1] == Targ[i - 1]) continue;
    int cc = Targ[i - 1];
    int d = (cc == 0 ? dist0[i] : dist1[i]);
    if (d <= 0) continue;
    int cur = i;
    vector<int> &dis = (cc == 0 ? dist0 : dist1);
    vector<int> &par = (cc == 0 ? par0 : par1);
    while (dis[cur] > 0) {
      req_t[cur] = dis[cur];
      req_c[cur] = cc;
      req_par[cur] = par[cur];
      cur = par[cur];
    }
  }
  // simulate
  vector<vector<int>> states;
  vector<int> curr = S;
  states.push_back(curr);
  int max_steps = lb * 2 + n;
  bool is_target = (curr == Targ);
  while (!is_target && states.size() - 1 < max_steps) {
    vector<int> nxt(n);
    int t = states.size();
    for (int i = 0; i < n; i++) {
      int id = i + 1;
      if (t == req_t[id] && req_c[id] != -1) {
        nxt[i] = req_c[id];
      } else {
        int tc = Targ[i];
        bool can = (curr[i] == tc);
        if (!can) {
          for (int j : adj[id]) {
            if (curr[j - 1] == tc) {
              can = true;
              break;
            }
          }
        }
        if (can) {
          nxt[i] = tc;
        } else {
          nxt[i] = curr[i];
        }
      }
    }
    curr = nxt;
    states.push_back(curr);
    is_target = (curr == Targ);
  }
  // output
  int kk = states.size() - 1;
  cout << kk << endl;
  for (auto &st : states) {
    for (int x : st) cout << x << " ";
    cout << endl;
  }
  return 0;
}