#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<vector<int>> count(n + 1, vector<int>(n + 1, 0));
  for (int i = 1; i <= n; i++) {
    for (int jj = 0; jj < n; jj++) {
      int c;
      cin >> c;
      count[i][c]++;
    }
  }
  auto compute_rem = [&]() -> int {
    int res = 0;
    for (int i = 1; i <= n; i++) {
      for (int j = 1; j <= n; j++) {
        if (j != i && count[i][j] > 0) {
          int dd = (j - i + n) % n;
          res += count[i][j] * dd;
        }
      }
    }
    return res;
  };
  int previous_rem = compute_rem();
  int stall_count = 0;
  vector<vector<int>> ops;
  int limit = n * (n - 1);
  while (previous_rem > 0 && (int)ops.size() < limit) {
    bool do_sacrifice = (stall_count >= n);
    vector<int> pass(n + 1, 0);
    for (int i = 1; i <= n; i++) {
      int best_r = -1;
      int best_j = n + 1;
      for (int j = 1; j <= n; j++) {
        if (count[i][j] == 0) continue;
        int r = (j == i ? 0 : (j - i + n) % n);
        bool allowed = !do_sacrifice || (r == 0);
        if (allowed && (r > best_r || (r == best_r && j < best_j))) {
          best_r = r;
          best_j = j;
        }
      }
      if (best_j > n) {
        // pass any available
        for (int j = 1; j <= n; j++) {
          if (count[i][j] > 0) {
            best_j = j;
            break;
          }
        }
      }
      pass[i] = best_j;
    }
    // perform passes
    vector<vector<int>> temp_count = count;
    for (int i = 1; i <= n; i++) {
      int j = pass[i];
      temp_count[i][j]--;
      int next_i = (i == n ? 1 : i + 1);
      temp_count[next_i][j]++;
    }
    count = temp_count;
    int new_rem = compute_rem();
    ops.push_back(vector<int>(pass.begin() + 1, pass.begin() + n + 1));
    if (new_rem == previous_rem) {
      stall_count++;
    } else {
      stall_count = 0;
    }
    previous_rem = new_rem;
  }
  cout << ops.size() << endl;
  for (auto& op : ops) {
    for (int d : op) {
      cout << d << " ";
    }
    cout << endl;
  }
  return 0;
}