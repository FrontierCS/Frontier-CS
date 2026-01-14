#include <bits/stdc++.h>
using namespace std;

int main() {
  int T;
  cin >> T;
  for (int t = 0; t < T; t++) {
    int n;
    cin >> n;
    vector<int> p(n + 1);
    for (int i = 1; i <= n; i++) cin >> p[i];
    vector<pair<int, int>> edgs(n - 1);
    vector<vector<pair<int, int>>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
      int u, v;
      cin >> u >> v;
      edgs[i] = {u, v};
      adj[u].push_back({v, i + 1});
      adj[v].push_back({u, i + 1});
    }
    // compute dist
    vector<vector<int>> distance(n + 1, vector<int>(n + 1, -1));
    for (int s = 1; s <= n; s++) {
      queue<int> q;
      q.push(s);
      distance[s][s] = 0;
      while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (auto [v, e] : adj[u]) {
          if (distance[s][v] == -1) {
            distance[s][v] = distance[s][u] + 1;
            q.push(v);
          }
        }
      }
    }
    // simulate
    vector<vector<int>> operations;
    vector<int> current_p = p;
    while (true) {
      bool is_done = true;
      for (int i = 1; i <= n; i++) {
        if (current_p[i] != i) {
          is_done = false;
          break;
        }
      }
      if (is_done) break;
      // collect candidates
      vector<pair<int, int>> cand_list;  // score, eid
      for (int i = 0; i < n - 1; i++) {
        int eid = i + 1;
        int u = edgs[i].first, v = edgs[i].second;
        int tu = current_p[u], tv = current_p[v];
        int dec1 = (tu == u ? 0 : distance[u][tu] - distance[v][tu]);
        int dec2 = (tv == v ? 0 : distance[v][tv] - distance[u][tv]);
        int score = 0;
        if (dec1 > 0) score += dec1;
        if (dec2 > 0) score += dec2;
        if (score > 0) {
          cand_list.emplace_back(score, eid);
        }
      }
      // sort descending score
      sort(cand_list.rbegin(), cand_list.rend());
      // greedy
      vector<bool> used(n + 1, false);
      vector<int> selected;
      for (auto& pr : cand_list) {
        int score = pr.first, eid = pr.second;
        int u = edgs[eid - 1].first, v = edgs[eid - 1].second;
        if (!used[u] && !used[v]) {
          selected.push_back(eid);
          used[u] = true;
          used[v] = true;
        }
      }
      // perform swaps
      for (int eid : selected) {
        int u = edgs[eid - 1].first, v = edgs[eid - 1].second;
        swap(current_p[u], current_p[v]);
      }
      // store sorted selected
      sort(selected.begin(), selected.end());
      operations.push_back(selected);
    }
    // output
    cout << operations.size() << endl;
    for (auto& op : operations) {
      cout << op.size();
      for (int e : op) cout << " " << e;
      cout << endl;
    }
  }
  return 0;
}