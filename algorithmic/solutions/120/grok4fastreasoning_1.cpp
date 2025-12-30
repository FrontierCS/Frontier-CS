#include <bits/stdc++.h>
using namespace std;

int main() {
  int n = 100;
  vector<vector<int>> adj(n + 1, vector<int>(n + 1, 0));
  auto qy = [&](int a, int b, int c) -> int {
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
  };
  // base 1 to 5
  vector<tuple<int, int, int>> triplets;
  vector<int> responses;
  for (int i = 1; i <= 5; ++i) {
    for (int j = i + 1; j <= 5; ++j) {
      for (int k = j + 1; k <= 5; ++k) {
        int res = qy(i, j, k);
        responses.push_back(res);
        triplets.emplace_back(i, j, k);
      }
    }
  }
  // enumerate
  map<pair<int, int>, int> edge_id;
  int num_e = 0;
  for (int i = 1; i <= 5; ++i) {
    for (int j = i + 1; j <= 5; ++j) {
      edge_id[{i, j}] = num_e++;
    }
  }
  bool found = false;
  for (int mask = 0; mask < (1 << 10); ++mask) {
    vector<vector<int>> temp_adj(6, vector<int>(6, 0));
    int temp_mask = mask;
    for (int i = 1; i <= 5; ++i) {
      for (int j = i + 1; j <= 5; ++j) {
        int val = (temp_mask & 1) ? 1 : 0;
        temp_adj[i][j] = temp_adj[j][i] = val;
        temp_mask >>= 1;
      }
    }
    // check
    bool match = true;
    int rid = 0;
    for (auto [i, j, k] : triplets) {
      int sum = temp_adj[i][j] + temp_adj[i][k] + temp_adj[j][k];
      if (sum != responses[rid]) {
        match = false;
        break;
      }
      ++rid;
    }
    if (match) {
      for (int i = 1; i <= 5; ++i) {
        for (int j = 1; j <= 5; ++j) {
          adj[i][j] = temp_adj[i][j];
        }
      }
      found = true;
      break;
    }
  }
  assert(found);
  // add 6 to 100
  for (int k = 6; k <= n; ++k) {
    int s = k - 1;
    int r = 1;
    vector<int> tt(s + 1, 0);
    for (int j = 1; j <= s; ++j) {
      if (j == r) continue;
      int res = qy(k, r, j);
      tt[j] = res - adj[r][j];
    }
    // cand0
    bool v0 = true;
    vector<int> x0(s + 1, 0);
    x0[r] = 0;
    for (int j = 1; j <= s; ++j) {
      if (j == r) continue;
      x0[j] = tt[j];
      if (x0[j] < 0 || x0[j] > 1) v0 = false;
    }
    // cand1
    bool v1 = true;
    vector<int> x1(s + 1, 0);
    x1[r] = 1;
    for (int j = 1; j <= s; ++j) {
      if (j == r) continue;
      x1[j] = tt[j] - 1;
      if (x1[j] < 0 || x1[j] > 1) v1 = false;
    }
    vector<int> chosen_x;
    if (v0 && v1) {
      // extra
      int j1 = (r == 1 ? 2 : 1);
      int j2 = (r == 2 ? 3 : (j1 == 2 ? 1 : 2));
      if (j2 == r) j2 = 4;
      int res = qy(k, j1, j2);
      int t_extra = res - adj[j1][j2];
      int sum0 = x0[j1] + x0[j2];
      int sum1 = x1[j1] + x1[j2];
      if (sum0 == t_extra) {
        chosen_x = x0;
      } else {
        chosen_x = x1;
      }
    } else if (v0) {
      chosen_x = x0;
    } else if (v1) {
      chosen_x = x1;
    } else {
      assert(false);
    }
    // set
    for (int i = 1; i <= s; ++i) {
      adj[k][i] = adj[i][k] = chosen_x[i];
    }
  }
  // output
  cout << "!" << endl;
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      cout << adj[i][j];
    }
    cout << endl;
  }
  cout.flush();
  return 0;
}