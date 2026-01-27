#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<vector<int>> adj(n + 1);
  for (int i = 0; i < n; ++i) {
    adj[i].push_back(i + 1);
  }
  vector<tuple<int, int, int>> added_list;
  auto bfs_reach = [&](int start, int maxd) -> vector<int> {
    vector<int> d(n + 1, -1);
    queue<pair<int, int>> q;
    q.push({start, 0});
    d[start] = 0;
    while (!q.empty()) {
      auto [pos, dep] = q.front();
      q.pop();
      if (dep >= maxd) continue;
      for (int nxt : adj[pos]) {
        if (d[nxt] == -1) {
          d[nxt] = dep + 1;
          q.push({nxt, dep + 1});
        }
      }
    }
    return d;
  };
  for (int v = n - 1; v >= 0; --v) {
    vector<int> d = bfs_reach(v, 3);
    bool covered = true;
    for (int u = v + 1; u <= n; ++u) {
      if (d[u] == -1 || d[u] > 3) {
        covered = false;
        break;
      }
    }
    while (!covered) {
      int best_score = -1;
      int best_c = -1;
      int best_w = -1;
      int best_missing = INT_MAX;
      int cover_w = -1;
      int cover_c = -1;
      for (int c : adj[v]) {
        for (int w : adj[c]) {
          if (w <= v) continue;
          bool has_direct = false;
          for (int x : adj[v]) {
            if (x == w) {
              has_direct = true;
              break;
            }
          }
          if (has_direct) continue;
          // simulate
          auto dw = bfs_reach(w, 2);
          vector<int> new_d = d;
          int this_missing = 0;
          bool this_cover = true;
          for (int u = v + 1; u <= n; ++u) {
            int oldd = new_d[u];
            int newdd = (dw[u] != -1 ? 1 + dw[u] : INT_MAX);
            int mindd = min(oldd == -1 ? INT_MAX : oldd, newdd);
            new_d[u] = mindd;
            if (mindd == INT_MAX || mindd > 3) {
              ++this_missing;
              this_cover = false;
            }
          }
          if (this_cover) {
            if (cover_w == -1 || w > cover_w) {
              cover_w = w;
              cover_c = c;
            }
            continue;
          }
          // non-cover score: number covered
          int score = (n - v) - this_missing;
          if (score > best_score) {
            best_score = score;
            best_c = c;
            best_w = w;
            best_missing = this_missing;
          }
        }
      }
      int chosen_w = -1;
      int chosen_c = -1;
      if (cover_w != -1) {
        chosen_w = cover_w;
        chosen_c = cover_c;
      } else if (best_w != -1) {
        chosen_w = best_w;
        chosen_c = best_c;
      } else {
        // add +2 if possible
        int ww = v + 2;
        if (ww > n) ww = n;
        bool has = false;
        for (int x : adj[v]) if (x == ww) has = true;
        if (!has && v + 1 <= n && find(adj[v].begin(), adj[v].end(), v + 1) != adj[v].end() &&
            find(adj[v + 1].begin(), adj[v + 1].end(), ww) != adj[v + 1].end()) {
          chosen_w = ww;
          chosen_c = v + 1;
        } else {
          // cannot add, but should not happen
          assert(false);
        }
      }
      // add it
      added_list.emplace_back(v, chosen_c, chosen_w);
      adj[v].push_back(chosen_w);
      // recompute full d
      d = bfs_reach(v, 3);
      // check covered
      covered = true;
      for (int u = v + 1; u <= n; ++u) {
        if (d[u] == -1 || d[u] > 3) {
          covered = false;
          break;
        }
      }
    }
  }
  cout << added_list.size() << endl;
  for (auto [u, c, vv] : added_list) {
    cout << u << " " << c << " " << vv << endl;
  }
  return 0;
}