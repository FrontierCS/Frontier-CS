#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M, H;
  cin >> N >> M >> H;
  vector<int> A(N);
  for (auto &x : A) cin >> x;
  vector<vector<int>> adj(N);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  vector<int> X(N), Y(N);
  for (int i = 0; i < N; i++) cin >> X[i] >> Y[i];
  vector<double> thetas;
  for (int i = 0; i < 12; i++) thetas.push_back(i * M_PI / 6.0);
  long long best_sc = -1;
  vector<int> best_par(N);
  for (double theta : thetas) {
    vector<double> proj(N);
    double c = cos(theta), s = sin(theta);
    for (int v = 0; v < N; v++) {
      proj[v] = X[v] * c + Y[v] * s;
    }
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
      if (proj[a] != proj[b]) return proj[a] > proj[b];
      return a < b;
    });
    vector<int> par(N, -1), dep(N, 0);
    for (int ii = 0; ii < N; ii++) {
      int v = order[ii];
      double pv = proj[v];
      int md = 0, bp = -1;
      for (int u : adj[v]) {
        double pu = proj[u];
        if (pu > pv + 1e-9) {
          int cd = dep[u] + 1;
          if (cd <= H && cd > md) {
            md = cd;
            bp = u;
          }
        }
      }
      dep[v] = md;
      if (md > 0) par[v] = bp;
    }
    long long sc = 0;
    for (int v = 0; v < N; v++) {
      sc += (dep[v] + 1LL) * A[v];
    }
    if (sc > best_sc) {
      best_sc = sc;
      best_par = par;
    }
  }
  for (int i = 0; i < N; i++) {
    if (i > 0) cout << " ";
    cout << best_par[i];
  }
  cout << endl;
}