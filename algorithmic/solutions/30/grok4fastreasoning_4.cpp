#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
  vector<int> t;
  Fenwick(int n) : t(n + 2, 0) {}
  void update(int i, int v = 1) {
    for (; i < (int)t.size(); i += i & -i) t[i] += v;
  }
  int query(int i) {
    int s = 0;
    for (; i > 0; i -= i & -i) s += t[i];
    return s;
  }
  int query(int l, int r) { return query(r) - query(l - 1); }
};

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
      int a, b;
      cin >> a >> b;
      adj[a].push_back(b);
      adj[b].push_back(a);
    }
    vector<int> par(n + 1, 0);
    vector<vector<int>> ch(n + 1);
    vector<int> dsz(n + 1, 0);
    vector<int> dtime(n + 1, 0);
    int tim = 1;
    function<void(int, int)> dfs = [&](int node, int p) {
      par[node] = p;
      dsz[node] = 1;
      dtime[node] = tim++;
      for (int nei : adj[node]) {
        if (nei == p) continue;
        ch[node].push_back(nei);
        dfs(nei, node);
        dsz[node] += dsz[nei];
      }
    };
    dfs(1, 0);
    vector<int> active;
    for (int i = 1; i <= n; i++) active.push_back(i);
    vector<int> cur(n + 1);
    for (int i = 1; i <= n; i++) cur[i] = i;
    bool done = false;
    while (!done && (int)active.size() > 1) {
      // check if all cur same
      int fc = cur[active[0]];
      bool same = true;
      for (int id : active) {
        if (cur[id] != fc) {
          same = false;
          break;
        }
      }
      if (same) {
        cout << "! " << fc << endl;
        cout.flush();
        done = true;
        continue;
      }
      // fenwick
      Fenwick ft(n + 1);
      for (int id : active) {
        ft.update(dtime[cur[id]], 1);
      }
      // find best x
      int bx = 1;
      int md = (int)active.size() + 1;
      for (int cx = 1; cx <= n; cx++) {
        int l = dtime[cx];
        int r = l + dsz[cx] - 1;
        int c1 = ft.query(l, r);
        int dif = abs(2 * c1 - (int)active.size());
        if (dif < md) {
          md = dif;
          bx = cx;
        }
      }
      // query
      cout << "? " << bx << endl;
      cout.flush();
      int res;
      cin >> res;
      // filter
      vector<int> na;
      for (int id : active) {
        int nd = cur[id];
        int l = dtime[bx];
        int r = l + dsz[bx] - 1;
        bool ins = (dtime[nd] >= l && dtime[nd] <= r);
        if ((ins ? 1 : 0) == res) {
          na.push_back(id);
          if (res == 0 && nd != 1) {
            cur[id] = par[nd];
          }
        }
      }
      active = na;
    }
    if (!done) {
      int thev = active[0];
      int ans = cur[thev];
      cout << "! " << ans << endl;
      cout.flush();
    }
  }
  return 0;
}