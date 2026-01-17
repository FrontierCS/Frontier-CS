#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<int> A(n);
  for (int &x : A) cin >> x;
  vector<int> T(n);
  for (int &x : T) cin >> x;
  vector<vector<int>> adj(n);
  for (int i = 0; i < m; i++) {
    int u, v;
    cin >> u >> v;
    u--; v--;
    adj[u].push_back(v);
    adj[v].push_back(u);
  }
  vector<vector<int>> states;
  states.push_back(A);
  vector<int> cur = A;
  int max_steps = 20000;
  while (states.size() <= max_steps + 1 && cur != T) {
    vector<int> next_state(n);
    bool changed = false;
    for (int i = 0; i < n; i++) {
      if (cur[i] == T[i]) {
        next_state[i] = cur[i];
        continue;
      }
      int needed = T[i];
      bool can = false;
      for (int j : adj[i]) {
        if (cur[j] == needed) {
          can = true;
          break;
        }
      }
      if (cur[i] == needed) can = true;
      if (can) {
        next_state[i] = needed;
        changed = true;
      } else {
        next_state[i] = cur[i];
      }
    }
    cur = next_state;
    states.push_back(cur);
    if (!changed) {
      // stuck, but continue to max
    }
  }
  int k = states.size() - 1;
  cout << k << endl;
  for (int t = 0; t <= k; t++) {
    for (int i = 0; i < n; i++) {
      if (i > 0) cout << " ";
      cout << states[t][i];
    }
    cout << endl;
  }
  return 0;
}