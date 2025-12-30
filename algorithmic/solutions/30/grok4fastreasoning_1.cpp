#include <bits/stdc++.h>
using namespace std;

int timer;
vector<int> in_t, out_t, sub_sum, depthh, par, cntt;
vector<vector<int>> adjj;

void dfs_time(int u, int p) {
  in_t[u] = timer++;
  for (int v : adjj[u]) if (v != p) dfs_time(v, u);
  out_t[u] = timer;
}

int compute_sub(int u, int p) {
  int s = cntt[u];
  for (int v : adjj[u]) if (v != p) s += compute_sub(v, u);
  sub_sum[u] = s;
  return s;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n;
    cin >> n;
    adjj.assign(n + 1, {});
    for (int i = 0; i < n - 1; i++) {
      int u, v;
      cin >> u >> v;
      adjj[u].push_back(v);
      adjj[v].push_back(u);
    }
    par.assign(n + 1, 0);
    depthh.assign(n + 1, 0);
    vector<bool> vis(n + 1, false);
    queue<int> qq;
    qq.push(1);
    vis[1] = true;
    par[1] = 1;
    depthh[1] = 0;
    while (!qq.empty()) {
      int u = qq.front();
      qq.pop();
      for (int v : adjj[u]) {
        if (!vis[v]) {
          vis[v] = true;
          par[v] = u;
          depthh[v] = depthh[u] + 1;
          qq.push(v);
        }
      }
    }
    timer = 0;
    in_t.assign(n + 1, 0);
    out_t.assign(n + 1, 0);
    dfs_time(1, -1);
    cntt.assign(n + 1, 1);
    int qcount = 0;
    int answer = -1;
    bool done = false;
    while (!done) {
      int num_dist = 0;
      int pos = -1;
      int total = 0;
      for (int i = 1; i <= n; i++) {
        if (cntt[i] > 0) {
          num_dist++;
          pos = i;
          total += cntt[i];
        }
      }
      if (num_dist <= 1) {
        if (num_dist == 1) {
          answer = pos;
        } else {
          answer = 1;
        }
        done = true;
        continue;
      }
      if (qcount >= 160) {
        answer = 1;
        done = true;
        continue;
      }
      compute_sub(1, -1);
      int best_worse = INT_MAX;
      int best_d = INT_MAX;
      int best_x = -1;
      for (int u = 1; u <= n; u++) {
        int c1 = sub_sum[u];
        int c0 = total - c1;
        int worse = max(c0, c1);
        if (worse < best_worse || (worse == best_worse && depthh[u] < best_d)) {
          best_worse = worse;
          best_d = depthh[u];
          best_x = u;
        }
      }
      if (best_x == -1) best_x = 1;
      qcount++;
      cout << "? " << best_x << endl;
      cout.flush();
      int r;
      cin >> r;
      vector<int> new_cnt(n + 1, 0);
      for (int w = 1; w <= n; w++) {
        if (cntt[w] == 0) continue;
        bool in_sub = (in_t[best_x] <= in_t[w] && out_t[w] <= out_t[best_x]);
        if (r == 1) {
          if (in_sub) {
            new_cnt[w] += cntt[w];
          }
        } else {
          if (!in_sub) {
            int target = (w == 1 ? 1 : par[w]);
            new_cnt[target] += cntt[w];
          }
        }
      }
      cntt = new_cnt;
    }
    cout << "! " << answer << endl;
    cout.flush();
  }
  return 0;
}