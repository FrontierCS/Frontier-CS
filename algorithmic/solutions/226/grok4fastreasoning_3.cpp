#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

ll mis(ll n, ll d) {
  if (d == 0 || d > n) return n;
  ll res = 0;
  for (ll r = 1; r <= d; ++r) {
    if (r > n) continue;
    ll count = (n - r) / d + 1;
    res += (count + 1) / 2;
  }
  return res;
}

ll f(ll n, ll x, ll y);

ll f(ll n, ll x, ll y) {
  if (n <= 0) return 0;
  if (x > y) swap(x, y);
  if (x == 0) return n;
  if (y >= n) return mis(n, x);
  if (x >= n) return n;
  if (x % 2 == 0 && y % 2 == 0) {
    ll n1 = (n + 1) / 2;
    ll n2 = n / 2;
    return f(n1, x / 2, y / 2) + f(n2, x / 2, y / 2);
  }
  if (x % 2 == 1 && y % 2 == 1) {
    return (n + 1) / 2;
  }
  // mixed
  ll even = (x % 2 == 0 ? x : y);
  return mis(n, even);
}

int main() {
  ll n, x, y;
  cin >> n >> x >> y;
  cout << f(n, x, y) << endl;
  return 0;
}