#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int cas = 0; cas < t; cas++) {
    int n, m, st, base_mc;
    cin >> n >> m >> st >> base_mc;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    vector<int> deg(n + 1);
    for (int i = 1; i <= n; i++) {
      deg[i] = adj[i].size();
    }
    vector<bool> vis(n + 1, false);
    int curr = st;
    vis[st] = true;
    int nvis = 1;
    while (true) {
      int D;
      cin >> D;
      vector<int> nbrd(D), nbrf(D);
      for (int j = 0; j < D; j++) {
        cin >> nbrd[j] >> nbrf[j];
      }
      vector<int> unvis_nbr;
      for (int v : adj[curr])
        if (!vis[v]) unvis_nbr.push_back(v);
      int ch_i = -1;
      int target_d = -1;
      if (!unvis_nbr.empty()) {
        map<int, int> deg_count;
        for (int v : adj[curr]) deg_count[deg[v]]++;
        int best_count = INT_MAX;
        int best_v = INT_MAX;
        for (int v : unvis_nbr) {
          int ct = deg_count[deg[v]];
          if (ct < best_count || (ct == best_count && v < best_v)) {
            best_count = ct;
            best_v = v;
          }
        }
        target_d = deg[best_v];
        for (int j = 0; j < D; j++) {
          if (nbrd[j] == target_d && nbrf[j] == 0) {
            ch_i = j;
            break;
          }
        }
      } else {
        int best_v = INT_MAX;
        for (int v : adj[curr]) {
          if (vis[v] && v < best_v) best_v = v;
        }
        target_d = deg[best_v];
        for (int j = 0; j < D; j++) {
          if (nbrd[j] == target_d && nbrf[j] == 1) {
            ch_i = j;
            break;
          }
        }
      }
      assert(ch_i != -1);
      cout << (ch_i + 1) << "\n";
      int the_flag = nbrf[ch_i];
      int the_deg = nbrd[ch_i];
      vector<int> poss_new;
      for (int v : adj[curr]) {
        if (deg[v] == the_deg && (vis[v] == (the_flag == 1))) {
          poss_new.push_back(v);
        }
      }
      assert(!poss_new.empty());
      int next_d;
      if (!(cin >> next_d)) {
        string res;
        cin >> res;
        break;
      }
      vector<int> next_nbrd(next_d), next_nbrf(next_d);
      for (int j = 0; j < next_d; j++) {
        cin >> next_nbrd[j] >> next_nbrf[j];
      }
      vector<pair<int, int>> obs;
      for (int j = 0; j < next_d; j++) {
        obs.emplace_back(next_nbrd[j], next_nbrf[j]);
      }
      sort(obs.begin(), obs.end());
      vector<int> matching;
      for (int pv : poss_new) {
        vector<pair<int, int>> expp;
        for (int w : adj[pv]) {
          int f = vis[w] ? 1 : 0;
          expp.emplace_back(deg[w], f);
        }
        sort(expp.begin(), expp.end());
        if (expp == obs) {
          matching.push_back(pv);
        }
      }
      int new_curr;
      if (matching.empty()) {
        sort(poss_new.begin(), poss_new.end());
        new_curr = poss_new[0];
      } else {
        sort(matching.begin(), matching.end());
        new_curr = matching[0];
      }
      curr = new_curr;
      if (the_flag == 0) {
        vis[new_curr] = true;
        nvis++;
      }
    }
  }
  return 0;
}