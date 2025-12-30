#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int cas = 0; cas < t; cas++) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    vector<int> par(n + 1, 0), dep(n + 1, 0);
    vector<vector<int>> ch(n + 1);
    vector<bool> visited(n + 1, false);
    queue<int> qq;
    qq.push(1);
    visited[1] = true;
    par[1] = 0;
    dep[1] = 0;
    while (!qq.empty()) {
      int u = qq.front();
      qq.pop();
      for (int v : adj[u]) {
        if (!visited[v]) {
          visited[v] = true;
          par[v] = u;
          dep[v] = dep[u] + 1;
          ch[u].push_back(v);
          qq.push(v);
        }
      }
    }
    int timer = 0;
    vector<int> intime(n + 1), outtime(n + 1);
    function<void(int)> dfss = [&](int u) {
      intime[u] = timer++;
      for (int v : ch[u]) dfss(v);
      outtime[u] = timer;
    };
    dfss(1);
    vector<int> possible;
    for (int i = 1; i <= n; i++) possible.push_back(i);
    int query_cnt = 0;
    while (possible.size() > 1) {
      int bestx = -1;
      int bestscore = INT_MAX / 2;
      for (size_t j = 0; j < possible.size(); j++) {
        int x = possible[j];
        int cnt1 = 0;
        for (int p : possible) {
          if (intime[x] <= intime[p] && intime[p] < outtime[x]) cnt1++;
        }
        bool hasv[5005];
        memset(hasv, 0, sizeof(hasv));
        int cnt0 = 0;
        for (int p : possible) {
          if (!(intime[x] <= intime[p] && intime[p] < outtime[x])) {
            int np = (p == 1 ? 1 : par[p]);
            if (!hasv[np]) {
              hasv[np] = true;
              cnt0++;
            }
          }
        }
        int score = max(cnt1, cnt0);
        if (score < bestscore) {
          bestscore = score;
          bestx = x;
        }
      }
      cout << "? " << bestx << endl;
      cout.flush();
      int resp;
      cin >> resp;
      query_cnt++;
      vector<int> newpossible;
      if (resp == 1) {
        for (int p : possible) {
          if (intime[bestx] <= intime[p] && intime[p] < outtime[bestx]) {
            newpossible.push_back(p);
          }
        }
      } else {
        bool hasv[5005];
        memset(hasv, 0, sizeof(hasv));
        for (int p : possible) {
          if (!(intime[bestx] <= intime[p] && intime[p] < outtime[bestx])) {
            int np = (p == 1 ? 1 : par[p]);
            if (!hasv[np]) {
              hasv[np] = true;
              newpossible.push_back(np);
            }
          }
        }
      }
      possible = std::move(newpossible);
    }
    cout << "! " << possible[0] << endl;
    cout.flush();
  }
  return 0;
}