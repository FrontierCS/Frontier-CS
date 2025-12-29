#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
  int N, M, K;
  cin >> N >> M >> K;
  vector<ll> X(N + 1), Y(N + 1);
  for (int i = 1; i <= N; i++) cin >> X[i] >> Y[i];
  vector<vector<tuple<int, int, ll>>> g(N + 1);
  for (int j = 0; j < M; j++) {
    int u, v;
    ll w;
    cin >> u >> v >> w;
    g[u].emplace_back(v, j, w);
    g[v].emplace_back(u, j, w);
  }
  vector<pair<ll, ll>> res(K);
  for (int k = 0; k < K; k++) {
    cin >> res[k].first >> res[k].second;
  }
  // Initial closest assignment to build S
  vector<ll> max_dsq(N + 1, 0);
  set<int> S;
  for (int k = 0; k < K; k++) {
    ll bx = res[k].first, by = res[k].second;
    ll best_d = LLONG_MAX / 2;
    int best_i = -1;
    for (int i = 1; i <= N; i++) {
      ll dx = X[i] - bx, dy = Y[i] - by;
      ll d = dx * dx + dy * dy;
      if (d < best_d) {
        best_d = d;
        best_i = i;
      }
    }
    max_dsq[best_i] = max(max_dsq[best_i], best_d);
    S.insert(best_i);
  }
  if (S.count(1) == 0 && !S.empty()) {
    // Still include 1 implicitly
  }
  // Dijkstra from 1
  vector<ll> dist(N + 1, LLONG_MAX / 2);
  vector<int> prev(N + 1, -1);
  dist[1] = 0;
  priority_queue<pair<ll, int>, vector<pair<ll, int>>, greater<pair<ll, int>>> pq;
  pq.emplace(0, 1);
  while (!pq.empty()) {
    auto [d, u] = pq.top();
    pq.pop();
    if (d > dist[u]) continue;
    for (auto [v, eid, ww] : g[u]) {
      ll nd = d + ww;
      if (nd < dist[v]) {
        dist[v] = nd;
        prev[v] = u;
        pq.emplace(nd, v);
      }
    }
  }
  // Collect used edges
  set<int> used_eids;
  for (int s : S) {
    if (s == 1) continue;
    int cur = s;
    while (cur != 1) {
      int par = prev[cur];
      for (auto [to, eid, ww] : g[cur]) {
        if (to == par) {
          used_eids.insert(eid);
          break;
        }
      }
      cur = par;
    }
  }
  // Collect reachable
  set<int> reachable;
  reachable.insert(1);
  for (int s : S) {
    if (s == 1) continue;
    int cur = s;
    while (cur != 1) {
      reachable.insert(cur);
      cur = prev[cur];
    }
  }
  // Now assign to closest in reachable
  vector<ll> max_dsq2(N + 1, 0);
  for (int k = 0; k < K; k++) {
    ll bx = res[k].first, by = res[k].second;
    ll best_d = LLONG_MAX / 2;
    int best_i = -1;
    for (int i : reachable) {
      ll dx = X[i] - bx, dy = Y[i] - by;
      ll d = dx * dx + dy * dy;
      if (d < best_d) {
        best_d = d;
        best_i = i;
      }
    }
    max_dsq2[best_i] = max(max_dsq2[best_i], best_d);
  }
  // Set P
  vector<ll> P(N + 1, 0);
  for (int i = 1; i <= N; i++) {
    ll need = max_dsq2[i];
    ll p = 0;
    while (p * p < need) p++;
    P[i] = min(p, 5000LL);
  }
  // B
  vector<int> B(M, 0);
  for (int e : used_eids) B[e] = 1;
  // Output
  for (int i = 1; i <= N; i++) {
    cout << P[i];
    if (i < N) cout << " ";
    else cout << "\n";
  }
  for (int j = 0; j < M; j++) {
    cout << B[j];
    if (j < M - 1) cout << " ";
    else cout << "\n";
  }
  return 0;
}