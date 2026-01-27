#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;
bool edge[MAXN][MAXN];
vector<int> adj[MAXN];
bool active[MAXN];
int cur_deg[MAXN];

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  for (int i = 0; i < M; i++) {
    int u, v;
    cin >> u >> v;
    if (u == v) continue;
    edge[u][v] = true;
    edge[v][u] = true;
  }
  for (int i = 1; i <= N; i++) {
    for (int j = 1; j <= N; j++) {
      if (edge[i][j]) {
        adj[i].push_back(j);
      }
    }
  }
  for (int i = 1; i <= N; i++) {
    active[i] = true;
    cur_deg[i] = adj[i].size();
  }
  vector<int> IS;
  while (true) {
    int min_d = INT_MAX;
    int best_v = -1;
    for (int i = 1; i <= N; i++) {
      if (active[i] && cur_deg[i] < min_d) {
        min_d = cur_deg[i];
        best_v = i;
      }
    }
    if (best_v == -1) break;
    IS.push_back(best_v);
    vector<int> to_delete;
    bool is_deleting[MAXN];
    memset(is_deleting, 0, sizeof(is_deleting));
    to_delete.push_back(best_v);
    is_deleting[best_v] = true;
    for (int u : adj[best_v]) {
      if (active[u]) {
        to_delete.push_back(u);
        is_deleting[u] = true;
      }
    }
    for (int t : to_delete) {
      for (int u : adj[t]) {
        if (active[u] && !is_deleting[u]) {
          cur_deg[u]--;
        }
      }
    }
    for (int t : to_delete) {
      active[t] = false;
    }
  }
  vector<int> ans(N + 1, 0);
  for (int v : IS) {
    ans[v] = 1;
  }
  for (int i = 1; i <= N; i++) {
    cout << ans[i] << '\n';
  }
  return 0;
}