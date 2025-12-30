#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  ll b;
  int k, w;
  cin >> b >> k >> w;
  vector<ll> U(k), V(k);
  // Query for U = x + y
  cout << "? 1 " << b << " " << b << endl;
  vector<ll> d(k);
  for (int i = 0; i < k; i++) cin >> d[i];
  for (int i = 0; i < k; i++) U[i] = 2 * b - d[i];
  // Query for V = x - y
  cout << "? 1 " << b << " -" << b << endl;
  vector<ll> e(k);
  for (int i = 0; i < k; i++) cin >> e[i];
  for (int i = 0; i < k; i++) V[i] = 2 * b - e[i];
  // Collect unique candidate (x, y)
  set<pair<ll, ll>> cands;
  for (int i = 0; i < k; i++) {
    for (int j = 0; j < k; j++) {
      ll u = U[i], v = V[j];
      if ((u + v) % 2 != 0) continue;
      ll x = (u + v) / 2;
      ll y = (u - v) / 2;
      if (abs(x) <= b && abs(y) <= b) {
        cands.insert({x, y});
      }
    }
  }
  // Now query each candidate
  vector<pair<ll, ll>> deposits;
  for (auto [x, y] : cands) {
    cout << "? 1 " << x << " " << y << endl;
    vector<ll> f(k);
    for (int i = 0; i < k; i++) cin >> f[i];
    int cnt = 0;
    for (ll val : f) if (val == 0) cnt++;
    for (int t = 0; t < cnt; t++) {
      deposits.emplace_back(x, y);
    }
  }
  // Output
  cout << "!";
  for (auto [x, y] : deposits) {
    cout << " " << x << " " << y;
  }
  cout << endl;
  return 0;
}