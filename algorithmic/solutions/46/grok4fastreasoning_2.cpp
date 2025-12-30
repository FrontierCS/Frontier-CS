#include <bits/stdc++.h>
using namespace std;

int main() {
  int J, M;
  cin >> J >> M;
  int N = J * M;
  vector<vector<int>> route(J, vector<int>(M));
  vector<vector<int>> proc(J, vector<int>(M));
  vector<vector<int>> op_pos(J, vector<int>(M));
  for(int j = 0; j < J; j++) {
    for(int k = 0; k < M; k++) {
      int m_, p_;
      cin >> m_ >> p_;
      route[j][k] = m_;
      proc[j][k] = p_;
      op_pos[j][m_] = k;
    }
  }
  vector<long long> total(J, 0);
  for(int j = 0; j < J; j++) for(int k = 0; k < M; k++) total[j] += proc[j][k];
  vector<int> init_perm(J);
  iota(init_perm.begin(), init_perm.end(), 0);
  sort(init_perm.begin(), init_perm.end(), [&](int a, int b) {
    if (total[a] != total[b]) return total[a] < total[b];
    return a < b;
  });
  vector<vector<int>> orders(M, init_perm);
  auto evaluate = [&](const vector<vector<int>>& ords) -> pair<bool, long long> {
    vector<vector<int>> order_index(M, vector<int>(J, -1));
    for (int m = 0; m < M; m++) {
      for (int i = 0; i < J; i++) {
        order_index[m][ords[m][i]] = i;
      }
    }
    vector<int> indeg(N, 0);
    for (int j = 0; j < J; j++) {
      for (int k = 1; k < M; k++) {
        indeg[j * M + k]++;
      }
    }
    for (int m = 0; m < M; m++) {
      for (int i = 0; i < J; i++) {
        int j = ords[m][i];
        int k = op_pos[j][m];
        int u = j * M + k;
        indeg[u] += i;
      }
    }
    vector<long long> dist(N, 0LL);
    queue<int> Q;
    for (int u = 0; u < N; u++) {
      if (indeg[u] == 0) {
        Q.push(u);
      }
    }
    int processed = 0;
    while (!Q.empty()) {
      int u = Q.front(); Q.pop();
      processed++;
      int j = u / M;
      int k = u % M;
      long long du = dist[u];
      long long p = proc[j][k];
      if (k < M - 1) {
        int v = j * M + (k + 1);
        dist[v] = max(dist[v], du + p);
        if (--indeg[v] == 0) {
          Q.push(v);
        }
      }
      int m_ = route[j][k];
      int i_pos = order_index[m_][j];
      for (int ii = i_pos + 1; ii < J; ii++) {
        int j2 = ords[m_][ii];
        int k2 = op_pos[j2][m_];
        int v = j2 * M + k2;
        long long ww = p;
        dist[v] = max(dist[v], du + ww);
        if (--indeg[v] == 0) {
          Q.push(v);
        }
      }
    }
    if (processed < N) return {false, 0LL};
    long long ms = 0;
    for (int j = 0; j < J; j++) {
      for (int k = 0; k < M; k++) {
        int u = j * M + k;
        ms = max(ms, dist[u] + (long long)proc[j][k]);
      }
    }
    return {true, ms};
  };
  bool global_improved = true;
  int max_outer = 20;
  int outer_count = 0;
  while (global_improved && outer_count < max_outer) {
    global_improved = false;
    outer_count++;
    for (int m = 0; m < M; m++) {
      bool local_improved = true;
      int max_local = J * 2;
      int local_count = 0;
      while (local_improved && local_count < max_local) {
        local_count++;
        auto [ok, curr_ms] = evaluate(orders);
        pair<int, int> best_swap = {-1, -1};
        long long best_ms = curr_ms;
        for (int i = 0; i < J - 1; i++) {
          swap(orders[m][i], orders[m][i + 1]);
          auto [tok, tms] = evaluate(orders);
          swap(orders[m][i], orders[m][i + 1]);
          if (tok && tms < best_ms) {
            best_ms = tms;
            best_swap = {i, i + 1};
          }
        }
        if (best_ms < curr_ms) {
          int i1 = best_swap.first;
          int i2 = best_swap.second;
          swap(orders[m][i1], orders[m][i2]);
          local_improved = true;
          global_improved = true;
        } else {
          local_improved = false;
        }
      }
    }
  }
  for (int m = 0; m < M; m++) {
    for (int i = 0; i < J; i++) {
      if (i > 0) cout << " ";
      cout << orders[m][i];
    }
    cout << endl;
  }
  return 0;
}