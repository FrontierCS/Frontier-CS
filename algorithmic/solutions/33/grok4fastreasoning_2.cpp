#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int get_size(ll t) {
  if (t == 1) return 0;
  if (t == 2) return 1;
  int l = 63 - __builtin_clzll(t);
  ll poww = 1LL << l;
  if (poww > t) {
    l--;
    poww >>= 1;
  }
  ll t2 = t - poww + 1;
  return l + get_size(t2);
}

vector<int> build(ll t, int lo, int hi) {
  int nn = hi - lo;
  if (t == 1) {
    return {};
  }
  if (t == 2) {
    return {lo};
  }
  int l = 63 - __builtin_clzll(t);
  ll poww = 1LL << l;
  if (poww > t) {
    l--;
    poww >>= 1;
  }
  ll t2 = t - poww + 1;
  int n2 = nn - l;
  int second_hi = lo + n2;
  vector<int> second = build(t2, lo, second_hi);
  vector<int> first(l);
  int first_lo = second_hi;
  for (int i = 0; i < l; i++) {
    first[i] = first_lo + i;
  }
  vector<int> res;
  res.reserve(nn);
  res.insert(res.end(), first.begin(), first.end());
  res.insert(res.end(), second.begin(), second.end());
  return res;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int q;
  cin >> q;
  for (int qq = 0; qq < q; qq++) {
    ll k;
    cin >> k;
    int n = get_size(k);
    vector<int> p = build(k, 0, n);
    cout << n << '\n';
    for (int i = 0; i < n; i++) {
      if (i) cout << " ";
      cout << p[i];
    }
    cout << '\n';
  }
}