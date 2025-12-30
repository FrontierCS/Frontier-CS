#include <bits/stdc++.h>
using namespace std;

vector<int> build(long long k) {
  if (k == 1) return {};
  if (k == 2) return {0};
  long long pp = 1;
  int b = 0;
  while (pp <= k / 2) {
    pp *= 2;
    b++;
  }
  long long p = pp;
  long long remain = k - p;
  long long ts = remain + 1;
  auto suf = build(ts);
  int ns = suf.size();
  int np = b;
  int n = np + ns;
  vector<int> pre(np);
  for (int i = 0; i < np; i++) pre[i] = i;
  vector<int> res(n);
  for (int i = 0; i < ns; i++) {
    res[np + i] = suf[i];
  }
  int base = ns;
  for (int i = 0; i < np; i++) {
    res[i] = base + pre[i];
  }
  return res;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int q;
  cin >> q;
  vector<long long> ks(q);
  for (auto &x : ks) cin >> x;
  for (auto k : ks) {
    auto perm = build(k);
    int n = perm.size();
    cout << n << '\n';
    for (int i = 0; i < n; i++) {
      if (i > 0) cout << " ";
      cout << perm[i];
    }
    cout << '\n';
  }
  return 0;
}