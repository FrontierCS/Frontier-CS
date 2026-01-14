#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  long long n_, x;
  cin >> n_ >> x;
  int n = n_;
  vector<long long> t(n + 1);
  for (int i = 1; i <= n; ++i) {
    cin >> t[i];
  }
  int left = 1;
  int bad_count = 0;
  int max_len = 1;
  int best_left = 1;
  int best_right = 1;
  for (int right = 1; right <= n; ++right) {
    bool added = false;
    if (right > 1) {
      if (t[right - 1] >= t[right]) {
        long long gamma = t[right - 1] - t[right] + 1;
        if (gamma > x) {
          left = right;
          bad_count = 0;
        } else {
          bad_count++;
          added = true;
        }
      }
    }
    while (bad_count > 10 && left < right) {
      if (t[left] >= t[left + 1]) {
        bad_count--;
      }
      left++;
    }
    int cur_len = right - left + 1;
    if (cur_len > max_len) {
      max_len = cur_len;
      best_left = left;
      best_right = right;
    }
  }
  cout << max_len << '\n';
  vector<int> bad_positions;
  for (int i = best_left; i < best_right; ++i) {
    if (t[i] >= t[i + 1]) {
      bad_positions.push_back(i);
    }
  }
  int op_idx = 0;
  for (int o = 0; o < 10; ++o) {
    if (op_idx < (int)bad_positions.size()) {
      int i = bad_positions[op_idx];
      long long d = t[i] - t[i + 1] + 1;
      int l = i + 1;
      int r = best_right;
      cout << l << " " << r << " " << d << "\n";
      ++op_idx;
    } else {
      cout << 1 << " " << 1 << " " << 0 << "\n";
    }
  }
}