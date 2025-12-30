#include <bits/stdc++.h>
using namespace std;

int main() {
  int J, M;
  cin >> J >> M;
  vector<vector<int>> route(J, vector<int>(M)), proc(J, vector<int>(M)), step(J, vector<int>(M, -1));
  for (int j = 0; j < J; j++) {
    for (int k = 0; k < M; k++) {
      int mch, p;
      cin >> mch >> p;
      route[j][k] = mch;
      proc[j][k] = p;
      step[j][mch] = k;
    }
  }
  vector<long long> total(J, 0);
  for (int j = 0; j < J; j++)
    for (int k = 0; k < M; k++) total[j] += proc[j][k];
  vector<int> pi(J);
  iota(pi.begin(), pi.end(), 0);
  sort(pi.begin(), pi.end(), [&](int a, int b) { return total[a] < total[b]; });
  auto compute_ms = [&](const vector<vector<int>>& orders) -> pair<bool, long long> {
    int N = J * M;
    int source = N;
    vector<vector<pair<int, int>>> g(N + 1);
    for (int j = 0; j < J; j++) {
      for (int k = 0; k < M - 1; k++) {
        int u = j * M + k;
        int v = j * M + k + 1;
        g[u].emplace_back(v, proc[j][k]);
      }
    }
    for (int m = 0; m < M; m++) {
      for (int i = 0; i < J - 1; i++) {
        int jb1 = orders[m][i];
        int jb2 = orders[m][i + 1];
        int k1 = step[jb1][m];
        int u = jb1 * M + k1;
        int k2 = step[jb2][m];
        int v = jb2 * M + k2;
        g[u].emplace_back(v, proc[jb1][k1]);
      }
    }
    for (int j = 0; j < J; j++) {
      int u = j * M + 0;
      g[source].emplace_back(u, 0);
    }
    vector<long long> dist(N + 1, 0);
    vector<int> indeg(N + 1, 0);
    for (int u = 0; u <= N; u++) {
      for (auto& p : g[u]) {
        indeg[p.first]++;
      }
    }
    queue<int> q;
    for (int u = 0; u <= N; u++) {
      if (indeg[u] == 0) q.push(u);
    }
    int vis = 0;
    while (!q.empty()) {
      int u = q.front();
      q.pop();
      vis++;
      for (auto& p : g[u]) {
        int v = p.first;
        int w = p.second;
        dist[v] = max(dist[v], dist[u] + (long long)w);
        if (--indeg[v] == 0) q.push(v);
      }
    }
    if (vis < N + 1) return {false, 0LL};
    long long ms = 0;
    for (int j = 0; j < J; j++) {
      for (int k = 0; k < M; k++) {
        int v = j * M + k;
        long long comp = dist[v] + (long long)proc[j][k];
        if (comp > ms) ms = comp;
      }
    }
    return {true, ms};
  };
  vector<vector<int>> current_orders(M, vector<int>(J));
  auto set_to_pi = [&](const vector<int>& pii) {
    for (int m = 0; m < M; m++) current_orders[m] = pii;
  };
  long long current_ms;
  bool valid;
  set_to_pi(pi);
  tie(valid, current_ms) = compute_ms(current_orders);
  bool improved = true;
  while (improved) {
    improved = false;
    vector<int> best_pi = pi;
    long long best_ms = current_ms;
    for (int pos = 0; pos < J - 1; pos++) {
      swap(pi[pos], pi[pos + 1]);
      set_to_pi(pi);
      auto [vl, msl] = compute_ms(current_orders);
      if (vl && msl < best_ms) {
        best_ms = msl;
        best_pi = pi;
      }
      swap(pi[pos], pi[pos + 1]);
    }
    if (best_ms < current_ms) {
      pi = best_pi;
      set_to_pi(pi);
      current_ms = best_ms;
      improved = true;
    }
  }
  set_to_pi(pi);
  improved = true;
  int max_iters = 100;
  int iter = 0;
  while (improved && iter++ < max_iters) {
    improved = false;
    for (int m = 0; m < M; m++) {
      vector<int> best_order_m = current_orders[m];
      long long best_ms = current_ms;
      for (int pos = 0; pos < J - 1; pos++) {
        swap(current_orders[m][pos], current_orders[m][pos + 1]);
        auto [vl, msl] = compute_ms(current_orders);
        if (vl && msl < best_ms) {
          best_ms = msl;
          best_order_m = current_orders[m];
        }
        swap(current_orders[m][pos], current_orders[m][pos + 1]);
      }
      if (best_ms < current_ms) {
        current_orders[m] = best_order_m;
        current_ms = best_ms;
        improved = true;
      }
    }
  }
  for (int m = 0; m < M; m++) {
    for (int i = 0; i < J; i++) {
      if (i > 0) cout << " ";
      cout << current_orders[m][i];
    }
    cout << endl;
  }
}