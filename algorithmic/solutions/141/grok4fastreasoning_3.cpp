#include <bits/stdc++.h>
using namespace std;

pair<int, vector<int>> compute(int L, int R, int k) {
  int s = R - L + 1;
  if (s <= k) {
    cout << "R" << endl;
    cout.flush();
    vector<int> reps;
    for (int i = L; i <= R; i++) {
      cout << "? " << i << endl;
      cout.flush();
      char ch;
      cin >> ch;
      if (ch == 'N') {
        reps.push_back(i);
      }
    }
    return {(int)reps.size(), reps};
  }
  int mid = (L + R) / 2;
  auto [dl, left_reps] = compute(L, mid, k);
  auto [dr, right_reps] = compute(mid + 1, R, k);
  int d1 = left_reps.size();
  int d2 = right_reps.size();
  if (d1 == 0) {
    return {dr, right_reps};
  }
  if (d2 == 0) {
    return {dl, left_reps};
  }
  // find best p, q
  long long min_cost = LLONG_MAX;
  int best_p = 1;
  int best_g1 = 1;
  for (int gp = 1; gp <= min(d1, k); gp++) {
    int pp = (d1 + gp - 1) / gp;
    int g1 = gp;
    int mg2 = (g1 == k ? 1 : k - g1);
    if (mg2 <= 0) continue;
    int qq = (d2 + mg2 - 1) / mg2;
    long long cost = (long long)pp * qq;
    if (cost < min_cost) {
      min_cost = cost;
      best_p = pp;
      best_g1 = g1;
    }
  }
  int p = best_p;
  int g1 = best_g1;
  int mg2 = (g1 == k ? 1 : k - g1);
  int q = (d2 + mg2 - 1) / mg2;
  // partition left into p groups of size ~g1
  vector<vector<int>> left_groups(p);
  int idx = 0;
  int base_l = d1 / p;
  int extra_l = d1 % p;
  for (int i = 0; i < p; i++) {
    int sz = base_l + (i < extra_l ? 1 : 0);
    sz = min(sz, g1);  // cap at g1
    for (int j = 0; j < sz; j++) {
      if (idx < d1) {
        left_groups[i].push_back(left_reps[idx++]);
      }
    }
  }
  // right into q groups of size ~mg2
  vector<vector<int>> right_groups(q);
  idx = 0;
  int base_r = d2 / q;
  int extra_r = d2 % q;
  for (int i = 0; i < q; i++) {
    int sz = base_r + (i < extra_r ? 1 : 0);
    sz = min(sz, mg2);
    for (int j = 0; j < sz; j++) {
      if (idx < d2) {
        right_groups[i].push_back(right_reps[idx++]);
      }
    }
  }
  // right_start
  vector<int> right_start(q, 0);
  idx = 0;
  for (int i = 0; i < q; i++) {
    right_start[i] = idx;
    idx += right_groups[i].size();
  }
  // is_new
  vector<bool> is_new_d2(d2, true);
  for (int ip = 0; ip < p; ip++) {
    int curr_g1 = left_groups[ip].size();
    for (int iq = 0; iq < q; iq++) {
      int curr_g2 = right_groups[iq].size();
      if (curr_g1 == 0 || curr_g2 == 0) continue;
      // batch
      cout << "R" << endl;
      cout.flush();
      // query curr_g1 left
      for (int r : left_groups[ip]) {
        cout << "? " << r << endl;
        cout.flush();
        char dummy;
        cin >> dummy;
      }
      // query curr_g2 right
      for (int jj = 0; jj < curr_g2; jj++) {
        int r = right_groups[iq][jj];
        cout << "? " << r << endl;
        cout.flush();
        char ch;
        cin >> ch;
        if (ch == 'Y') {
          int gi = right_start[iq] + jj;
          if (gi < d2) is_new_d2[gi] = false;
        }
      }
    }
  }
  // count
  int num_new = 0;
  vector<int> new_reps;
  for (int ii = 0; ii < d2; ii++) {
    if (is_new_d2[ii]) {
      num_new++;
      new_reps.push_back(right_reps[ii]);
    }
  }
  vector<int> union_reps = left_reps;
  union_reps.insert(union_reps.end(), new_reps.begin(), new_reps.end());
  int total_d = dl + num_new;
  return {total_d, union_reps};
}

int main() {
  int n, k;
  cin >> n >> k;
  auto [d, reps] = compute(1, n, k);
  cout << "! " << d << endl;
  cout.flush();
  return 0;
}