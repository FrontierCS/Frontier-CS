#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int tt = 0; tt < t; tt++) {
    int n, m, startv, basec;
    cin >> n >> m >> startv >> basec;
    vector<vector<int>> adj(n + 1);
    vector<int> degree(n + 1, 0);
    for (int i = 0; i < m; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
      degree[u]++;
      degree[v]++;
    }
    int visited_count = 1;
    vector<int> path_deg;
    path_deg.push_back(degree[startv]);
    bool done = false;
    while (!done) {
      string token;
      cin >> token;
      if (token == "AC" || token == "F") {
        done = true;
        continue;
      }
      int d = stoi(token);
      vector<pair<int, int>> neigh(d);
      for (int i = 0; i < d; i++) {
        int dg, fl;
        cin >> dg >> fl;
        neigh[i] = {dg, fl};
      }
      int chosen = -1;
      bool is_explore = false;
      int next_d = -1;
      bool success_backtrack = false;
      if (visited_count == n) {
        chosen = (d > 0 ? 1 : 1);
        next_d = (d > 0 ? neigh[0].first : 0);
      } else {
        int un_idx = -1;
        for (int i = 0; i < d; i++) {
          if (neigh[i].second == 0) {
            un_idx = i;
            break;
          }
        }
        if (un_idx != -1) {
          is_explore = true;
          chosen = un_idx + 1;
          next_d = neigh[un_idx].first;
        } else {
          is_explore = false;
          int pdeg = (path_deg.size() > 1 ? path_deg[path_deg.size() - 2] : -1);
          int bt_idx = -1;
          if (pdeg != -1) {
            for (int i = 0; i < d; i++) {
              if (neigh[i].second == 1 && neigh[i].first == pdeg) {
                bt_idx = i;
                break;
              }
            }
          }
          if (bt_idx != -1) {
            chosen = bt_idx + 1;
            next_d = pdeg;
            success_backtrack = true;
          } else {
            int fb_idx = -1;
            for (int i = 0; i < d; i++) {
              if (neigh[i].second == 1) {
                fb_idx = i;
                break;
              }
            }
            if (fb_idx != -1) {
              chosen = fb_idx + 1;
              next_d = neigh[fb_idx].first;
              is_explore = true;
            } else {
              chosen = (d > 0 ? 1 : 1);
              next_d = (d > 0 ? neigh[0].first : 0);
              is_explore = true;
            }
            success_backtrack = false;
          }
        }
      }
      cout << chosen << endl;
      cout.flush();
      if (visited_count == n) {
        // no update
      } else if (is_explore && neigh[chosen - 1].second == 0) {
        visited_count++;
        path_deg.push_back(next_d);
      } else if (success_backtrack) {
        path_deg.pop_back();
      } else {
        path_deg.push_back(next_d);
      }
    }
  }
  return 0;
}