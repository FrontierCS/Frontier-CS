#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M, H;
  cin >> N >> M >> H;
  vector<int> A(N);
  for (int i = 0; i < N; i++) cin >> A[i];
  vector<vector<int>> adj(N);
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  vector<int> X(N), Y(N);
  for (int i = 0; i < N; i++) {
    cin >> X[i] >> Y[i];
  }
  // Compute cover_ball
  vector<bitset<1000>> cover_ball(N);
  for (int s = 0; s < N; s++) {
    vector<int> dist(N, -1);
    dist[s] = 0;
    queue<int> qq;
    qq.push(s);
    while (!qq.empty()) {
      int u = qq.front(); qq.pop();
      cover_ball[s][u] = 1;
      if (dist[u] == H) continue;
      for (int v : adj[u]) {
        if (dist[v] == -1) {
          dist[v] = dist[u] + 1;
          if (dist[v] <= H) {
            qq.push(v);
          }
        }
      }
    }
  }
  // Select roots
  bitset<1000> uncovered;
  for (int i = 0; i < N; i++) uncovered[i] = 1;
  vector<int> roots;
  while (uncovered.count() > 0) {
    int best_u = -1;
    int max_new = -1;
    int min_a = INT_MAX;
    for (int u = 0; u < N; u++) {
      bitset<1000> potential_new = cover_ball[u] & uncovered;
      int cnt = potential_new.count();
      if (cnt > 0) {
        int aa = A[u];
        if (cnt > max_new || (cnt == max_new && aa < min_a)) {
          max_new = cnt;
          min_a = aa;
          best_u = u;
        }
      }
    }
    if (best_u == -1) {
      // Fallback
      for (int u = 0; u < N; u++) {
        if (uncovered[u]) {
          best_u = u;
          break;
        }
      }
    }
    roots.push_back(best_u);
    uncovered &= ~cover_ball[best_u];
  }
  // Multi-source BFS
  vector<int> parent(N, -1);
  vector<int> dep(N, -1);
  vector<bool> assigned(N, false);
  queue<int> q;
  for (int r : roots) {
    if (assigned[r]) continue;
    assigned[r] = true;
    dep[r] = 0;
    parent[r] = -1;
    q.push(r);
  }
  while (!q.empty()) {
    int u = q.front(); q.pop();
    if (dep[u] == H) continue;
    for (int v : adj[u]) {
      if (!assigned[v]) {
        int newdep = dep[u] + 1;
        if (newdep > H) continue;
        assigned[v] = true;
        dep[v] = newdep;
        parent[v] = u;
        q.push(v);
      }
    }
  }
  // Handle any unassigned (should not happen)
  for (int i = 0; i < N; i++) {
    if (!assigned[i]) {
      parent[i] = -1;
      dep[i] = 0;
      assigned[i] = true;
    }
  }
  // Output
  for (int i = 0; i < N; i++) {
    if (i > 0) cout << " ";
    cout << parent[i];
  }
  cout << endl;
  return 0;
}