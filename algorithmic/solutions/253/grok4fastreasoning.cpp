#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int cas = 0; cas < t; cas++) {
    int n, m;
    cin >> n >> m;
    vector<int> A(m + 1), B(m + 1);
    vector<vector<int>> adj(n + 1);
    for (int i = 1; i <= m; i++) {
      cin >> A[i] >> B[i];
      adj[A[i]].push_back(i);
      adj[B[i]].push_back(i);
    }
    // block all
    vector<bool> is_blocked(m + 1, false);
    for (int i = 1; i <= m; i++) {
      cout << "- " << i << '\n';
      is_blocked[i] = true;
    }
    cout.flush();
    // find s
    int s = -1;
    for (int y = 1; y <= n; y++) {
      cout << "? 1 " << y << '\n';
      cout.flush();
      int r;
      cin >> r;
      if (r == -1) return 0;
      if (r == 1) {
        s = y;
      }
    }
    // discovery
    vector<bool> discovered(n + 1, false);
    discovered[s] = true;
    vector<int> distance(n + 1, -1);
    distance[s] = 0;
    queue<int> que;
    que.push(s);
    vector<bool> tested(m + 1, false);
    vector<bool> repaired(m + 1, false);
    while (!que.empty()) {
      int u = que.front();
      que.pop();
      for (int road : adj[u]) {
        int v = (A[road] == u ? B[road] : A[road]);
        if (discovered[v]) continue;
        // test
        cout << "+ " << road << '\n';
        cout.flush();
        is_blocked[road] = false;
        tested[road] = true;
        cout << "? 1 " << v << '\n';
        cout.flush();
        int r;
        cin >> r;
        if (r == -1) return 0;
        if (r == 1) {
          repaired[road] = true;
          discovered[v] = true;
          distance[v] = distance[u] + 1;
          que.push(v);
          // leave unblocked
        } else {
          repaired[road] = false;
          cout << "- " << road << '\n';
          cout.flush();
          is_blocked[road] = true;
        }
      }
    }
    // second phase
    for (int i = 1; i <= m; i++) {
      if (tested[i]) continue;
      tested[i] = true;
      int x = A[i], y = B[i];
      int u = x, v = y;
      if (distance[u] > distance[v]) {
        u = y;
        v = x;
      }
      // isolate v
      cout << "+ " << i << '\n';
      cout.flush();
      is_blocked[i] = false;
      vector<int> temp_blocked;
      for (int j : adj[v]) {
        if (j == i) continue;
        if (!is_blocked[j]) {
          cout << "- " << j << '\n';
          cout.flush();
          is_blocked[j] = true;
          temp_blocked.push_back(j);
        }
      }
      cout << "? 1 " << v << '\n';
      cout.flush();
      int r;
      cin >> r;
      if (r == -1) return 0;
      repaired[i] = (r == 1);
      // restore
      for (int j : temp_blocked) {
        cout << "+ " << j << '\n';
        cout.flush();
        is_blocked[j] = false;
      }
      cout << "- " << i << '\n';
      cout.flush();
      is_blocked[i] = true;
    }
    // output
    cout << "!";
    for (int i = 1; i <= m; i++) {
      cout << " " << (repaired[i] ? 1 : 0);
    }
    cout << '\n';
    cout.flush();
    int verdict;
    cin >> verdict;
    if (verdict == 0) return 0;
  }
  return 0;
}