#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n, m, start, base_move_count;
    cin >> n >> m >> start >> base_move_count;
    vector<vector<int>> adj(n + 1);
    vector<int> degree(n + 1, 0);
    for (int i = 0; i < m; ++i) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
      ++degree[u];
      ++degree[v];
    }
    set<int> visited_set;
    visited_set.insert(start);
    int curr = start;
    vector<int> path_stack{start};
    // Read first description
    int current_d;
    cin >> current_d;
    vector<pair<int, int>> current_neigh(current_d);
    for (int i = 0; i < current_d; ++i) {
      int dd, f;
      cin >> dd >> f;
      current_neigh[i] = {dd, f};
    }
    bool done = false;
    while (!done) {
      // Build type_idx
      map<pair<int, int>, vector<int>> type_idx;
      for (int i = 0; i < current_d; ++i) {
        auto [dd, f] = current_neigh[i];
        type_idx[{dd, f}].push_back(i + 1);
      }
      // Decide choice
      int choice = 1;
      // Prefer unique new or smallest group new
      int min_count = INT_MAX;
      pair<int, int> best_tp = {-1, -1};
      int min_d = INT_MAX;
      bool has_new = false;
      for (auto& p : type_idx) {
        auto tp = p.first;
        if (tp.second == 0) {
          has_new = true;
          int cnt = p.second.size();
          if (cnt == 1 || (cnt < min_count) || (cnt == min_count && tp.first < min_d)) {
            min_count = cnt;
            min_d = tp.first;
            best_tp = tp;
          }
        }
      }
      if (has_new) {
        // Choose the best_tp
        choice = type_idx[best_tp][0];
      } else {
        // Backtrack
        int par = (path_stack.size() >= 2) ? path_stack[path_stack.size() - 2] : -1;
        if (par != -1) {
          pair<int, int> ptp = {degree[par], 1};
          auto it = type_idx.find(ptp);
          if (it != type_idx.end() && !it->second.empty()) {
            choice = it->second[0];
          }
        }
        // else choice remains 1
      }
      // Output
      cout << choice << endl;
      fflush(stdout);
      // Now read next
      int new_d;
      cin >> new_d;
      if (cin.fail()) {
        cin.clear();
        string ss;
        cin >> ss;
        done = true;
        continue;
      }
      vector<pair<int, int>> new_neigh(new_d);
      for (int i = 0; i < new_d; ++i) {
        int dd, f;
        cin >> dd >> f;
        new_neigh[i] = {dd, f};
      }
      // Disambiguate new_curr
      int idx = choice - 1;
      int chosen_dd = current_neigh[idx].first;
      int chosen_f = current_neigh[idx].second;
      // Candidates
      vector<int> candidates;
      for (int w : adj[curr]) {
        bool vis = visited_set.count(w);
        if (degree[w] == chosen_dd && (vis ? 1 : 0) == chosen_f) {
          candidates.push_back(w);
        }
      }
      // Received sorted
      vector<pair<int, int>> received_sorted = new_neigh;
      sort(received_sorted.begin(), received_sorted.end());
      // Find matching
      vector<int> matching;
      for (int w : candidates) {
        vector<pair<int, int>> expected;
        for (int x : adj[w]) {
          bool vis = visited_set.count(x);
          expected.emplace_back(degree[x], vis ? 1 : 0);
        }
        sort(expected.begin(), expected.end());
        if (expected == received_sorted) {
          matching.push_back(w);
        }
      }
      int new_curr;
      if (matching.empty()) {
        new_curr = candidates.empty() ? curr : candidates[0];
      } else {
        sort(matching.begin(), matching.end());
        new_curr = matching[0];  // smallest label
      }
      // Update
      curr = new_curr;
      bool was_new = (chosen_f == 0);
      if (was_new && visited_set.find(curr) == visited_set.end()) {
        visited_set.insert(curr);
      }
      // Update path
      if (!path_stack.empty() && curr == path_stack.back()) {
        path_stack.pop_back();
      } else {
        path_stack.push_back(curr);
      }
      // Update current_neigh
      current_d = new_d;
      current_neigh = std::move(new_neigh);
    }
  }
  return 0;
}