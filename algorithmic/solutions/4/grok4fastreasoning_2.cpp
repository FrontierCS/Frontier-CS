#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  long long k;
  cin >> n >> k;
  vector<vector<long long>> cache(n + 1, vector<long long>(n + 1, LLONG_MIN));
  auto get = [&](int i, int j) -> long long {
    if (cache[i][j] != LLONG_MIN) return cache[i][j];
    cout << "QUERY " << i << " " << j << endl;
    cout.flush();
    long long v;
    cin >> v;
    cache[i][j] = v;
    return v;
  };
  long long minv = get(1, 1);
  long long maxv = get(n, n);
  auto count_leq = [&](long long x) -> long long {
    long long tot = 0;
    int cur = n;
    for (int row = 1; row <= n; ++row) {
      while (cur >= 1) {
        long long val = get(row, cur);
        if (val <= x) break;
        --cur;
      }
      if (cur >= 1) {
        tot += cur;
      } else {
        return tot;
      }
    }
    return tot;
  };
  long long l = minv, r = maxv;
  while (l < r) {
    long long m = l + (r - l) / 2;
    if (count_leq(m) >= k) {
      r = m;
    } else {
      l = m + 1;
    }
  }
  cout << "DONE " << l << endl;
  cout.flush();
  return 0;
}