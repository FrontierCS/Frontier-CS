#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m, k;
  double eps;
  cin >> n >> m >> k >> eps;
  vector<vector<int>> adj(n + 1);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    if (u != v) {
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
  }
  vector<int> deg(n + 1, 0);
  for (int i = 1; i <= n; i++) {
    sort(adj[i].begin(), adj[i].end());
    auto it = unique(adj[i].begin(), adj[i].end());
    adj[i].erase(it, adj[i].end());
    deg[i] = adj[i].size();
  }
  auto bipartition = [&](const vector<int>& S, int target_a) -> vector<int> {
    int ns = S.size();
    if (target_a <= 0 || ns == 0) return {};
    int seed = -1;
    int max_d = -1;
    for (int v : S) {
      if (deg[v] > max_d || (deg[v] == max_d && (seed == -1 || v < seed))) {
        max_d = deg[v];
        seed = v;
      }
    }
    if (seed == -1) return {};
    vector<int> A{seed};
    vector<char> in_A(n + 1, 0);
    in_A[seed] = 1;
    vector<char> in_S_(n + 1, 0);
    for (int v : S) in_S_[v] = 1;
    vector<int> boundary(n + 1, 0);
    for (int u : adj[seed]) {
      if (in_S_[u] && !in_A[u]) boundary[u]++;
    }
    int current_size = 1;
    while (current_size < target_a) {
      int best_v = -1;
      int max_b = -1;
      for (int v : S) {
        if (in_A[v]) continue;
        int b = boundary[v];
        bool better = (b > max_b) || (b == max_b && (best_v == -1 || v < best_v));
        if (better) {
          max_b = b;
          best_v = v;
        }
      }
      if (best_v == -1) break;
      A.push_back(best_v);
      in_A[best_v] = 1;
      current_size++;
      for (int u : adj[best_v]) {
        if (in_S_[u] && !in_A[u]) boundary[u]++;
      }
    }
    return A;
  };
  vector<int> part(n + 1, 0);
  vector<int> allv(n);
  iota(allv.begin(), allv.end(), 1);
  function<void(const vector<int>&, int, int)> partition_func = [&](const vector<int>& S, int first_label, int num_labels) {
    if (S.empty() || num_labels <= 0) return;
    if (num_labels == 1) {
      for (int v : S) part[v] = first_label;
      return;
    }
    int sub_num = num_labels / 2;
    int target_size = S.size() / 2;
    vector<int> left = bipartition(S, target_size);
    vector<char> is_left(n + 1, 0);
    for (int v : left) is_left[v] = 1;
    vector<int> right;
    right.reserve(S.size() - left.size());
    for (int v : S) {
      if (!is_left[v]) right.push_back(v);
    }
    partition_func(left, first_label, sub_num);
    partition_func(right, first_label + sub_num, sub_num);
  };
  partition_func(allv, 1, k);
  for (int i = 1; i <= n; i++) {
    cout << part[i];
    if (i < n) cout << " ";
    else cout << "\n";
  }
  return 0;
}