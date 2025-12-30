#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  long long n, m;
  int k;
  double eps;
  cin >> n >> m >> k >> eps;
  vector<vector<int>> adj(n + 1);
  for (long long i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    if (u != v) {
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
  }
  for (int i = 1; i <= n; i++) {
    sort(adj[i].begin(), adj[i].end());
    auto it = unique(adj[i].begin(), adj[i].end());
    adj[i].erase(it, adj[i].end());
  }
  long long ideal = (n + k - 1) / k;
  long long maxs = floor((1 + eps) * ideal);
  vector<int> verts(n);
  for (int i = 0; i < n; i++) verts[i] = i + 1;
  mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
  shuffle(verts.begin(), verts.end(), rng);
  vector<int> part(n + 1, 0);
  vector<long long> sizes(k + 1, 0);
  int idx = 0;
  for (int p = 1; p <= k; p++) {
    long long szp = n / k + (p <= (n % k) ? 1 : 0);
    for (long long j = 0; j < szp; j++) {
      int v = verts[idx++];
      part[v] = p;
      sizes[p]++;
    }
  }
  int K1 = k + 1;
  size_t flat_size = (n + 1LL) * K1;
  vector<int> all_counts(flat_size, 0);
  auto get_idx = [K1](int v, int q) { return v * K1 + q; };
  int num_iters = 20;
  for (int iter = 0; iter < num_iters; iter++) {
    fill(all_counts.begin(), all_counts.end(), 0);
    for (int u = 1; u <= n; u++) {
      for (int v : adj[u]) {
        int q = part[v];
        all_counts[get_idx(u, q)]++;
      }
    }
    for (int u = 1; u <= n; u++) {
      int P = part[u];
      int degP = all_counts[get_idx(u, P)];
      int best_delta = 0;
      int bestQ = P;
      for (int Q = 1; Q <= k; Q++) {
        if (Q == P) continue;
        int degQ = all_counts[get_idx(u, Q)];
        int delta = degP - degQ;
        if (delta < best_delta && sizes[Q] < maxs) {
          best_delta = delta;
          bestQ = Q;
        }
      }
      if (best_delta < 0) {
        sizes[P]--;
        sizes[bestQ]++;
        part[u] = bestQ;
      }
    }
  }
  for (int i = 1; i <= n; i++) {
    if (i > 1) cout << " ";
    cout << part[i];
  }
  cout << "\n";
  return 0;
}