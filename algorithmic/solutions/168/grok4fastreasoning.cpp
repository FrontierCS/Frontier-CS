#include <bits/stdc++.h>
using namespace std;

int main() {
  srand(time(NULL));
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
  for (int i = 0; i < N; i++) {
    int dummy1, dummy2;
    cin >> dummy1 >> dummy2;
  }
  vector<int> best_parent(N, 0);
  long long best_score = -1LL << 60;
  const int ATTEMPTS = 20;
  for (int att = 0; att < ATTEMPTS; att++) {
    vector<pair<int, int>> sorter(N);
    for (int i = 0; i < N; i++) {
      int key = A[i] * 10000 + (rand() % 10000);
      sorter[i] = {key, i};
    }
    sort(sorter.begin(), sorter.end());
    vector<int> order(N);
    for (int i = 0; i < N; i++) order[i] = sorter[i].second;
    vector<int> level(N, -1);
    vector<int> parent(N, -1);
    for (int v : order) {
      int max_prev = -1;
      int best_u = -1;
      for (int u : adj[v]) {
        if (level[u] != -1 && level[u] <= H - 1 && level[u] > max_prev) {
          max_prev = level[u];
          best_u = u;
        }
      }
      int l = (max_prev == -1 ? 0 : max_prev + 1);
      if (max_prev != -1) parent[v] = best_u;
      level[v] = l;
    }
    long long score = 0;
    for (int v = 0; v < N; v++) {
      score += 1LL * level[v] * A[v];
    }
    if (score > best_score) {
      best_score = score;
      best_parent = parent;
    }
  }
  for (int i = 0; i < N; i++) {
    if (i > 0) cout << " ";
    cout << best_parent[i];
  }
  cout << endl;
  return 0;
}