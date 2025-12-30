#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> perm(n);
  for (int i = 0; i < n; i++) {
    cin >> perm[i];
  }
  vector<pair<int, int>> operations;
  auto apply_op = [&](auto&& self, vector<int>& arr, int x, int y) -> void {
    vector<int> new_perm(n);
    int suf_start = n - y;
    for (int i = 0; i < y; i++) {
      new_perm[i] = arr[suf_start + i];
    }
    int mid_start = x;
    int mid_len = n - x - y;
    for (int i = 0; i < mid_len; i++) {
      new_perm[y + i] = arr[mid_start + i];
    }
    int pre_len = x;
    for (int i = 0; i < pre_len; i++) {
      new_perm[n - pre_len + i] = arr[i];
    }
    arr = new_perm;
  };
  if (n == 3) {
    vector<int> orig = perm;
    vector<int> sw = {perm[2], perm[1], perm[0]};
    if (sw < orig) {
      operations.emplace_back(1, 1);
    }
  } else {
    int pos1 = -1;
    for (int i = 0; i < n; i++) {
      if (perm[i] == 1) {
        pos1 = i;
        break;
      }
    }
    if (pos1 != 0) {
      if (pos1 == 1) {
        apply_op(apply_op, perm, 2, 1);
        operations.emplace_back(2, 1);
        apply_op(apply_op, perm, 1, 1);
        operations.emplace_back(1, 1);
      } else {
        int k = pos1 + 1;
        int y = n - k + 1;
        int x = 1;
        apply_op(apply_op, perm, x, y);
        operations.emplace_back(x, y);
      }
    }
    int current_fixed = 1;
    for (int targ = 2; targ <= n - 2; targ++) {
      int j = -1;
      for (int i = current_fixed - 1; i < n; i++) {
        if (perm[i] == targ) {
          j = i;
          break;
        }
      }
      int l = n - current_fixed + 1;
      int local_pos = j - (current_fixed - 1);
      if (local_pos == 1) {
        current_fixed++;
        continue;
      }
      int d = local_pos - 1;
      int chosen_d1 = -1, chosen_d2 = -1;
      for (int try1 = 1; try1 < l; try1++) {
        int need = (d - try1 + l) % l;
        if (need >= 1 && need <= l - 1) {
          chosen_d1 = try1;
          chosen_d2 = need;
          break;
        }
      }
      assert(chosen_d1 != -1);
      int yg = l - chosen_d1;
      int xg = current_fixed;
      apply_op(apply_op, perm, xg, yg);
      operations.emplace_back(xg, yg);
      int xp = l - chosen_d2;
      int yp = current_fixed;
      apply_op(apply_op, perm, xp, yp);
      operations.emplace_back(xp, yp);
      current_fixed++;
    }
    if (perm[n - 2] != n - 1 || perm[n - 1] != n) {
      vector<pair<int, int>> fixes = {{1, 1}, {1, 2}, {1, 1}, {2, 1}, {1, 1}};
      for (auto p : fixes) {
        apply_op(apply_op, perm, p.first, p.second);
        operations.push_back(p);
      }
    }
  }
  cout << operations.size() << '\n';
  for (auto p : operations) {
    cout << p.first << ' ' << p.second << '\n';
  }
}