#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<int> par(N+1, 0);
  vector<vector<int>> adj(N+1);
  for(int i = 1; i < N; i++) {
    int p;
    cin >> p;
    int ch = i + 1;
    par[ch] = p;
    adj[p].push_back(ch);
    adj[ch].push_back(p);
  }
  vector<int> leaf_list;
  for(int i = 1; i <= N; i++) {
    if(adj[i].size() == 1) {
      leaf_list.push_back(i);
    }
  }
  sort(leaf_list.begin(), leaf_list.end());
  int kk = leaf_list.size();
  vector<vector<int>> all_X(N + 2 * kk + 1);
  int next_id = N + 1;
  vector<pair<int, int>> tree_edges;
  // main X and edges
  for(int u = 1; u <= N; u++) {
    vector<int> x = {u};
    if(par[u]) x.push_back(par[u]);
    sort(x.begin(), x.end());
    all_X[u] = x;
  }
  for(int u = 2; u <= N; u++) {
    tree_edges.emplace_back(par[u], u);
  }
  // added for leaves
  for(int ii = 0; ii < kk; ii++) {
    int l = leaf_list[ii];
    int p = par[l];
    int prev_idx = (ii + kk - 1) % kk;
    int next_idx = (ii + 1) % kk;
    int prevv = leaf_list[prev_idx];
    int nextv = leaf_list[next_idx];
    // prev
    vector<int> x_prev = {l, p, prevv};
    sort(x_prev.begin(), x_prev.end());
    auto it = unique(x_prev.begin(), x_prev.end());
    x_prev.resize(it - x_prev.begin());
    all_X[next_id] = x_prev;
    int prevbag = next_id++;
    tree_edges.emplace_back(l, prevbag);
    // next
    vector<int> x_next = {l, p, nextv};
    sort(x_next.begin(), x_next.end());
    it = unique(x_next.begin(), x_next.end());
    x_next.resize(it - x_next.begin());
    all_X[next_id] = x_next;
    int nextbag = next_id++;
    tree_edges.emplace_back(l, nextbag);
  }
  int K = next_id - 1;
  cout << K << '\n';
  for(int i = 1; i <= K; i++) {
    const auto& xx = all_X[i];
    cout << xx.size();
    for(int vv : xx) {
      cout << " " << vv;
    }
    cout << '\n';
  }
  for(auto& e : tree_edges) {
    cout << e.first << " " << e.second << '\n';
  }
  return 0;
}