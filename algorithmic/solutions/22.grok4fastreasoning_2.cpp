#include <bits/stdc++.h>
using namespace std;

int N, next_id;
vector<vector<int>> children, local_leaves, all_X;
vector<pair<int, int>> new_tree_edges;

int get_new_id() {
  int id = next_id++;
  all_X[id] = {};
  return id;
}

void dfs(int u) {
  vector<int> leaves;
  for (int v : children[u]) {
    dfs(v);
    leaves.insert(leaves.end(), local_leaves[v].begin(), local_leaves[v].end());
  }
  if (children[u].empty()) {
    leaves = {u};
  }
  local_leaves[u] = leaves;
}

int build(int u, bool root_cycle) {
  const auto& le = local_leaves[u];
  int m = le.size();
  vector<int> sub_attach;
  for (int v : children[u]) {
    int att = build(v, false);
    sub_attach.push_back(att);
  }
  vector<int> bag_ids;
  int local_attach = -1;
  if (m == 1) {
    int id = get_new_id();
    all_X[id] = {u};
    local_attach = id;
  } else if (m <= 3) {
    int id = get_new_id();
    all_X[id] = {u};
    for (int l : le) all_X[id].push_back(l);
    bag_ids.push_back(id);
    local_attach = id;
  } else if (m == 4) {
    int id1 = get_new_id();
    all_X[id1] = {u, le[0], le[1], le[2]};
    int id2 = get_new_id();
    if (root_cycle) {
      all_X[id2] = {u, le[2], le[3], le[0]};
    } else {
      all_X[id2] = {u, le[1], le[2], le[3]};
    }
    new_tree_edges.push_back({id1, id2});
    bag_ids = {id1, id2};
    local_attach = id1;
  } else {
    // m > 4
    for (int ii = 0; ii < m - 2; ++ii) {
      int id = get_new_id();
      all_X[id] = {u, le[ii], le[ii + 1], le[ii + 2]};
      bag_ids.push_back(id);
    }
    if (!root_cycle) {
      for (size_t j = 0; j + 1 < bag_ids.size(); ++j) {
        new_tree_edges.push_back({bag_ids[j], bag_ids[j + 1]});
      }
      local_attach = bag_ids[0];
    } else {
      // root, add closing
      int closing = get_new_id();
      all_X[closing] = {u, le[m - 1], le[0], le[1]};
      vector<int> all_leaf_bags = bag_ids;
      all_leaf_bags.push_back(closing);
      // build clusters
      int num = m - 2;
      int clus_sz = 4;
      vector<vector<int>> clusters;
      for (int st = 0; st < num; st += clus_sz) {
        vector<int> cl;
        int endd = min(st + clus_sz, num);
        for (int p = st; p < endd; ++p) {
          cl.push_back(bag_ids[p]);
        }
        for (size_t p = 0; p + 1 < cl.size(); ++p) {
          new_tree_edges.push_back({cl[p], cl[p + 1]});
        }
        clusters.push_back(cl);
      }
      // add closing to last cluster
      if (!clusters.empty()) {
        int lc = clusters.size() - 1;
        if (!clusters[lc].empty()) {
          new_tree_edges.push_back({clusters[lc].back(), closing});
        }
        clusters[lc].push_back(closing);
      }
      // wrapping chain
      int chain = get_new_id();
      all_X[chain] = {u, le[m - 1], le[0], le[1]};
      local_attach = chain;
      // attach first and last clusters to chain
      if (!clusters.empty()) {
        // first
        new_tree_edges.push_back({clusters[0][0], chain});
        // last
        new_tree_edges.push_back({closing, chain});
        // middle
        for (size_t ci = 1; ci + 1 < clusters.size(); ++ci) {
          new_tree_edges.push_back({clusters[ci][0], chain});
        }
      }
      // set bag_ids to all_leaf_bags for picking, but since vector<int> all_leaf_bags defined here, wait
      // wait, for attaching children, we need all_leaf_bags
      // so, move the all_leaf_bags before
      // wait, in code, after adding closing, before clusters, vector<int> all_leaf_bags = bag_ids; all_leaf_bags.push_back(closing);
      // then use all_leaf_bags for picking chosen
      // yes, set bag_ids = all_leaf_bags; // for the loop below to use bag_ids as all_leaf_bags
      bag_ids = all_leaf_bags;
    }
  }
  // now attach children
  int pos = 0;
  size_t num_child = children[u].size();
  for (size_t ci = 0; ci < num_child; ++ci) {
    int v = children[u][ci];
    int this_pos = pos;
    int sz = local_leaves[v].size();
    int sub_att = sub_attach[ci];
    int spoke = get_new_id();
    all_X[spoke] = {u, v};
    int chosen;
    if (bag_ids.empty()) {
      chosen = local_attach;
    } else {
      int jj = max(0, this_pos - 2);
      if (jj >= (int)bag_ids.size()) jj = bag_ids.size() - 1;
      chosen = bag_ids[jj];
    }
    new_tree_edges.push_back({spoke, chosen});
    new_tree_edges.push_back({spoke, sub_att});
    pos += sz;
  }
  return local_attach;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  cin >> N;
  children.resize(N + 1);
  local_leaves.resize(N + 1);
  for (int i = 1; i < N; ++i) {
    int p;
    cin >> p;
    children[p].push_back(i + 1);
  }
  dfs(1);
  all_X.resize(4 * N + 10);
  next_id = 1;
  build(1, true);
  int K = next_id - 1;
  cout << K << '\n';
  for (int i = 1; i <= K; ++i) {
    vector<int> s = all_X[i];
    sort(s.begin(), s.end());
    cout << s.size();
    for (int x : s) {
      cout << " " << x;
    }
    cout << '\n';
  }
  for (auto e : new_tree_edges) {
    int a = e.first, b = e.second;
    if (a > b) swap(a, b);
    cout << a << " " << b << '\n';
  }
  return 0;
}