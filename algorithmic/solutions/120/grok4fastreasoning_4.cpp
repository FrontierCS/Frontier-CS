#include <bits/stdc++.h>
using namespace std;

int main() {
  int adj[101][101];
  memset(adj, 0, sizeof(adj));
  // base 1-4
  vector<tuple<int, int, int>> base_queries = {
    {1, 2, 3},
    {1, 2, 4},
    {1, 3, 4},
    {2, 3, 4}
  };
  vector<int> qs(4);
  for (int idx = 0; idx < 4; idx++) {
    auto [a, b, c] = base_queries[idx];
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    cin >> qs[idx];
  }
  // enumerate
  int good_mask = -1;
  int count_good = 0;
  for (int mask = 0; mask < 64; mask++) {
    int e12 = mask & 1;
    int e13 = (mask >> 1) & 1;
    int e14 = (mask >> 2) & 1;
    int e23 = (mask >> 3) & 1;
    int e24 = (mask >> 4) & 1;
    int e34 = (mask >> 5) & 1;
    int c1 = e12 + e13 + e23;
    int c2 = e12 + e14 + e24;
    int c3 = e13 + e14 + e34;
    int c4 = e23 + e24 + e34;
    if (c1 == qs[0] && c2 == qs[1] && c3 == qs[2] && c4 == qs[3]) {
      good_mask = mask;
      count_good++;
    }
  }
  // assume count_good == 1
  assert(count_good == 1);
  int e12 = good_mask & 1;
  int e13 = (good_mask >> 1) & 1;
  int e14 = (good_mask >> 2) & 1;
  int e23 = (good_mask >> 3) & 1;
  int e24 = (good_mask >> 4) & 1;
  int e34 = (good_mask >> 5) & 1;
  adj[1][2] = adj[2][1] = e12;
  adj[1][3] = adj[3][1] = e13;
  adj[1][4] = adj[4][1] = e14;
  adj[2][3] = adj[3][2] = e23;
  adj[2][4] = adj[4][2] = e24;
  adj[3][4] = adj[4][3] = e34;
  // add 5 to 100
  for (int v = 5; v <= 100; v++) {
    int k = v - 1;
    int pivot = 1;
    vector<int> ss(k - 1);
    for (int j = 0; j < k - 1; j++) {
      int i = j + 2;
      cout << "? " << pivot << " " << i << " " << v << endl;
      cout.flush();
      int qq;
      cin >> qq;
      ss[j] = qq - adj[pivot][i];
    }
    bool all_one = true;
    for (int val : ss) {
      if (val != 1) all_one = false;
    }
    vector<int> e(k + 1, 0);
    if (all_one && k >= 3) {
      int i1 = 2, i2 = 3;
      cout << "? " << i1 << " " << i2 << " " << v << endl;
      cout.flush();
      int qq;
      cin >> qq;
      int d = qq - adj[i1][i2];
      if (d == 2) {
        e[pivot] = 0;
        for (int ii = 1; ii <= k; ii++) {
          if (ii != pivot) e[ii] = 1;
        }
      } else {
        e[pivot] = 1;
        for (int ii = 1; ii <= k; ii++) {
          if (ii != pivot) e[ii] = 0;
        }
      }
    } else {
      bool pos0 = true;
      for (int val : ss) {
        if (val > 1) pos0 = false;
      }
      if (pos0) {
        e[pivot] = 0;
        for (int j = 0; j < k - 1; j++) {
          int i = j + 2;
          e[i] = ss[j];
        }
      } else {
        bool pos1 = true;
        for (int val : ss) {
          if (val < 1) pos1 = false;
        }
        assert(pos1);
        e[pivot] = 1;
        for (int j = 0; j < k - 1; j++) {
          int i = j + 2;
          e[i] = ss[j] - 1;
        }
      }
    }
    for (int i = 1; i <= k; i++) {
      adj[i][v] = e[i];
      adj[v][i] = e[i];
    }
  }
  // output
  cout << "!" << endl;
  cout.flush();
  for (int i = 1; i <= 100; i++) {
    for (int j = 1; j <= 100; j++) {
      cout << adj[i][j];
    }
    cout << endl;
  }
  cout.flush();
  return 0;
}