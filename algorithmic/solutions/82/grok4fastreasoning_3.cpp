#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n;
  cin >> n;
  vector<long long> perm(n + 1, -1LL);
  const long long ALL_BITS = (1LL << 12) - 1;
  const int MAX_L = 1 << 12;
  auto get_possible = [&](long long com, long long msk, int nn) -> vector<long long> {
    vector<long long> res;
    vector<int> bitlist;
    for (int k = 0; k < 12; ++k) {
      if (msk & (1LL << k)) bitlist.push_back(k);
    }
    int nb = bitlist.size();
    for (int st = 0; st < (1 << nb); ++st) {
      long long s = 0;
      for (int i = 0; i < nb; ++i) {
        if (st & (1 << i)) s |= (1LL << bitlist[i]);
      }
      long long xx = com | s;
      if (xx < nn) res.push_back(xx);
    }
    return res;
  };
  // Top level star from 1
  int top_ref = 1;
  vector<long long> top_o(n + 1, 0);
  for (int j = 2; j <= n; ++j) {
    cout << "? " << top_ref << " " << j << '\n';
    cout.flush();
    long long val;
    cin >> val;
    if (val == -1) return 0;
    top_o[j] = val;
  }
  // Find the_pr for top_ref
  vector<long long> top_vs(n);
  for (int i = 0; i < n; ++i) top_vs[i] = i;
  long long top_pr = -1;
  int top_nump = 0;
  for (auto pr_try : top_vs) {
    vector<int> pos_c(MAX_L, 0);
    for (int j = 2; j <= n; ++j) {
      long long ljj = top_o[j] & ((~pr_try) & ALL_BITS);
      pos_c[(int)ljj]++;
    }
    vector<int> val_c(MAX_L, 0);
    for (auto x : top_vs) {
      if (x == pr_try) continue;
      long long lxx = x & ((~pr_try) & ALL_BITS);
      val_c[(int)lxx]++;
    }
    bool match = true;
    for (int ll = 0; ll < MAX_L && match; ++ll) {
      if (pos_c[ll] != val_c[ll]) match = false;
    }
    if (match) {
      top_nump++;
      top_pr = pr_try;
    }
  }
  assert(top_nump == 1);
  perm[top_ref] = top_pr;
  // Now groups for 2 to n
  vector<vector<int>> top_groups(MAX_L);
  for (int j = 2; j <= n; ++j) {
    long long lj = top_o[j] & ((~top_pr) & ALL_BITS);
    int idx = (int)lj;
    top_groups[idx].push_back(j);
  }
  // Recursive solve lambda
  auto solve = [&](auto&& self, const vector<int>& poss, long long com, long long cmsk) -> void {
    int sz = poss.size();
    if (sz == 0) return;
    if (sz == 1) {
      auto vs = get_possible(com, cmsk, n);
      assert(vs.size() == 1);
      perm[poss[0]] = vs[0];
      return;
    }
    // Pick ref
    int ref = poss[0];
    vector<long long> local_o(sz);
    for (int ii = 1; ii < sz; ++ii) {
      int jj = poss[ii];
      cout << "? " << ref << " " << jj << '\n';
      cout.flush();
      long long val;
      cin >> val;
      if (val == -1) return 0;
      local_o[ii] = val;
    }
    // Get vs
    auto vs = get_possible(com, cmsk, n);
    // Find pr
    long long lpr = -1;
    int lnump = 0;
    for (auto pr_try : vs) {
      vector<int> pos_c(MAX_L, 0);
      for (int ii = 1; ii < sz; ++ii) {
        long long ljj = local_o[ii] & ((~pr_try) & ALL_BITS);
        pos_c[(int)ljj]++;
      }
      vector<int> val_c(MAX_L, 0);
      for (auto x : vs) {
        if (x == pr_try) continue;
        long long lxx = x & ((~pr_try) & ALL_BITS);
        val_c[(int)lxx]++;
      }
      bool match = true;
      for (int ll = 0; ll < MAX_L && match; ++ll) {
        if (pos_c[ll] != val_c[ll]) match = false;
      }
      if (match) {
        lnump++;
        lpr = pr_try;
      }
    }
    assert(lnump == 1);
    perm[ref] = lpr;
    // Groups
    vector<vector<int>> lgroups(MAX_L);
    for (int ii = 1; ii < sz; ++ii) {
      int jj = poss[ii];
      long long lj = local_o[ii] & ((~lpr) & ALL_BITS);
      int idx = (int)lj;
      lgroups[idx].push_back(jj);
    }
    for (int ll = 0; ll < MAX_L; ++ll) {
      if (!lgroups[ll].empty()) {
        vector<int> subp = lgroups[ll];
        self(self, subp, (long long)ll, lpr);
      }
    }
  };
  // Call recursions
  for (int ll = 0; ll < MAX_L; ++ll) {
    if (!top_groups[ll].empty()) {
      solve(solve, top_groups[ll], (long long)ll, top_pr);
    }
  }
  // Output
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << perm[i];
  }
  cout << '\n';
  cout.flush();
  return 0;
}