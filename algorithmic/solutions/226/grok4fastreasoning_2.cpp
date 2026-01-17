#include <bits/stdc++.h>

using namespace std;

typedef long long ll;

int main() {
  ll n, x, y;
  cin >> n >> x >> y;
  if (x > y) swap(x, y);
  ll ans = 0;
  for (ll r = 1; r <= x; ++r) {
    if (r > n) break;
    ll num = (n - r) / x + 1;
    ans += (num + 1) / 2;
  }
  cout << ans << endl;
  return 0;
}