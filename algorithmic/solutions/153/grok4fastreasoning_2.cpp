#include <bits/stdc++.h>
using namespace std;

struct UF {
  vector<int> par, sz;
  UF(int n) : par(n), sz(n, 1) {
    iota(par.begin(), par.end(), 0);
  }
  int find(int x) {
    return par[x] == x ? x : par[x] = find(par[x]);
  }
  bool unite(int a, int b) {
    a = find(a);
    b = find(b);
    if (a == b) return false;
    if (sz[a] < sz[b]) swap(a, b);
    par[b] = a;
    sz[a] += sz[b];
    return true;
  }
};

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int N = 400;
  int M = 1995;
  vector<int> x(N), y(N);
  for (int i = 0; i < N; i++) {
    cin >> x[i] >> y[i];
  }
  vector<pair<int, int>> ed(M);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    ed[i] = {u, v};
  }
  vector<int> d(M);
  for (int i = 0; i < M; i++) {
    auto [u, v] = ed[i];
    int dx = x[u] - x[v];
    int dy = y[u] - y[v];
    double dist = sqrt(1.0 * dx * dx + 1.0 * dy * dy);
    d[i] = round(dist);
  }
  UF uf(N);
  for (int i = 0; i < M; i++) {
    int l;
    cin >> l;
    auto [u, v] = ed[i];
    int pu = uf.find(u);
    int pv = uf.find(v);
    if (pu == pv) {
      cout << 0 << endl;
      continue;
    }
    // compute current_find
    vector<int> current_find(N);
    for (int node = 0; node < N; node++) {
      current_find[node] = uf.find(node);
    }
    // collect roots
    set<int> roots_set;
    for (int node = 0; node < N; node++) {
      roots_set.insert(current_find[node]);
    }
    vector<int> roots(roots_set.begin(), roots_set.end());
    int K = roots.size();
    // super_id
    vector<int> super_id(N, -1);
    for (int j = 0; j < K; j++) {
      super_id[roots[j]] = j;
    }
    // super UF
    UF super_uf(K);
    // process remaining
    for (int j = i + 1; j < M; j++) {
      int uu = ed[j].first;
      int vv = ed[j].second;
      int puu = current_find[uu];
      int pvv = current_find[vv];
      if (puu != pvv) {
        int sid1 = super_id[puu];
        int sid2 = super_id[pvv];
        super_uf.unite(sid1, sid2);
      }
    }
    // count super components
    set<int> super_roots;
    for (int j = 0; j < K; j++) {
      super_roots.insert(super_uf.find(j));
    }
    bool remaining_connect = (super_roots.size() == 1);
    // decide
    double r = (double)l / d[i];
    double threshold = 2.0;
    bool want_add = (r <= threshold);
    bool add_it = true;
    if (remaining_connect && !want_add) {
      add_it = false;
    }
    if (add_it) {
      uf.unite(u, v);
      cout << 1 << endl;
    } else {
      cout << 0 << endl;
    }
  }
  return 0;
}