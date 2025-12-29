#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, M, K;
  cin >> N >> M >> K;
  vector<ll> X(N + 1), Y(N + 1);
  for (int i = 1; i <= N; i++) {
    cin >> X[i] >> Y[i];
  }
  struct E {
    int u, v, id;
    ll w;
  };
  vector<E> alledges(M);
  int eid[101][101];
  memset(eid, -1, sizeof(eid));
  for (int j = 0; j < M; j++) {
    int u, v;
    ll w;
    cin >> u >> v >> w;
    alledges[j] = {u, v, j + 1, w};
    eid[u][v] = j + 1;
    eid[v][u] = j + 1;
  }
  vector<ll> A(K + 1), B(K + 1);
  for (int k = 1; k <= K; k++) {
    cin >> A[k] >> B[k];
  }
  // compute assignment
  vector<ll> max_d2(N + 1, 0);
  for (int k = 1; k <= K; k++) {
    ll min_d = LLONG_MAX / 2;
    int best = -1;
    for (int i = 1; i <= N; i++) {
      ll dx = X[i] - A[k];
      ll dy = Y[i] - B[k];
      ll d2 = dx * dx + dy * dy;
      if (d2 < min_d) {
        min_d = d2;
        best = i;
      }
    }
    max_d2[best] = max(max_d2[best], min_d);
  }
  // compute P
  vector<int> P(N + 1, 0);
  for (int i = 1; i <= N; i++) {
    if (max_d2[i] == 0) continue;
    ll d = max_d2[i];
    ll low = 0, high = 5001;
    while (low < high) {
      ll mid = (low + high) / 2;
      if (mid * mid >= d) {
        high = mid;
      } else {
        low = mid + 1;
      }
    }
    P[i] = (int)low;
    if (P[i] > 5000) P[i] = 5000;
  }
  // useful
  set<int> useful;
  for (int i = 1; i <= N; i++) {
    if (P[i] > 0 || i == 1) useful.insert(i);
  }
  // MST
  vector<int> par(N + 1);
  iota(par.begin(), par.end(), 0);
  auto find = [&](auto&& self, int x) -> int {
    return par[x] == x ? x : par[x] = self(self, par[x]);
  };
  auto unite = [&](int x, int y) {
    x = find(find, x);
    y = find(find, y);
    if (x != y) par[x] = y;
  };
  sort(alledges.begin(), alledges.end(), [](const E& a, const E& b) {
    return a.w < b.w;
  });
  vector<vector<pair<int, int>>> tree(N + 1); // to, eid
  for (auto& e : alledges) {
    int pu = find(find, e.u);
    int pv = find(find, e.v);
    if (pu != pv) {
      unite(e.u, e.v);
      tree[e.u].push_back({e.v, e.id});
      tree[e.v].push_back({e.u, e.id});
    }
  }
  // dfs for num_useful
  vector<int> num_useful(N + 1, 0);
  function<void(int, int)> dfs = [&](int u, int prev) {
    num_useful[u] = useful.count(u) ? 1 : 0;
    for (auto [v, id] : tree[u]) {
      if (v == prev) continue;
      dfs(v, u);
      num_useful[u] += num_useful[v];
    }
  };
  dfs(1, -1);
  // mark
  vector<bool> on_edge(M + 1, false);
  function<void(int, int)> mark = [&](int u, int prev) {
    for (auto [v, id] : tree[u]) {
      if (v == prev) continue;
      if (num_useful[v] > 0) {
        on_edge[id] = true;
      }
      mark(v, u);
    }
  };
  mark(1, -1);
  // output
  for (int i = 1; i <= N; i++) {
    if (i > 1) cout << " ";
    cout << P[i];
  }
  cout << "\n";
  for (int j = 1; j <= M; j++) {
    if (j > 1) cout << " ";
    cout << (on_edge[j] ? 1 : 0);
  }
  cout << "\n";
  return 0;
}