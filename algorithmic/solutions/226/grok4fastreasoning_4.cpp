#include <bits/stdc++.h>

using namespace std;

typedef long long ll;

ll solve(ll n, ll x, ll y) {
  if (n <= 0) return 0;
  if (x == 0 || y == 0) return n;
  if (x > y) swap(x, y);
  if (x == 0) return n;
  if (x % 2 == 1 && y % 2 == 1) return (n + 1LL) / 2;
  if (x % 2 == 0 && y % 2 == 0) {
    ll k1 = n / 2;
    ll k2 = n - k1;
    return solve(k1, x / 2, y / 2) + solve(k2, x / 2, y / 2);
  }
  // mixed
  return (n + 1LL) / 2;
}

int main() {
  ll n, x, y;
  cin >> n >> x >> y;
  cout << solve(n, x, y) << endl;
  return 0;
}