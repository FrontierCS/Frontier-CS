#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1000000007LL;
ll modpow(ll base, ll exp, ll mod) {
  ll res = 1;
  base %= mod;
  while (exp > 0) {
    if (exp & 1) res = (__int128)res * base % mod;
    base = (__int128)base * base % mod;
    exp >>= 1;
  }
  return res;
}
ll modinv(ll x, ll mod) { return modpow(x, mod-2, mod); }
ll discrete_log(ll g, ll y, ll mod) {
  if (y == 1) return 0;
  ll ord = mod - 1;
  ll step = 0;
  while (step * step < ord) step++;
  step++;
  map<ll, ll> babies;
  ll cur = 1;
  for (ll i = 0; i < step; ++i) {
    babies[cur] = i;
    cur = (__int128)cur * g % mod;
  }
  ll gstep = modpow(g, step, mod);
  ll inv_gstep = modinv(gstep, mod);
  cur = y;
  for (ll j = 0; j < step; ++j) {
    auto it = babies.find(cur);
    if (it != babies.end()) {
      return j * step + it->second;
    }
    cur = (__int128)cur * inv_gstep % mod;
  }
  assert(false);
  return -1;
}
int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  ll g = 3;
  vector<int> operators(n+1, 0);
  int current_pos = 1;
  while (current_pos <= n) {
    int group_start = current_pos;
    int group_size = min(29, n - current_pos + 1);
    vector<ll> a(n+1, 1LL);
    for (int loc = 0; loc < group_size; ++loc) {
      int k = current_pos + loc;
      ll exp = (1LL << loc);
      a[k] = modpow(g, exp, MOD);
    }
    cout << "?";
    for (int i = 0; i <= n; ++i) {
      ll val = (i == 0 ? 1LL : a[i]);
      cout << " " << val;
    }
    cout << "\n";
    cout.flush();
    ll res1;
    cin >> res1;
    cout << "?";
    for (int i = 0; i <= n; ++i) {
      ll val = (i == 0 ? 2LL : a[i]);
      cout << " " << val;
    }
    cout << "\n";
    cout.flush();
    ll res2;
    cin >> res2;
    ll alpha = (res2 - res1 + MOD) % MOD;
    ll e = discrete_log(g, alpha, MOD);
    for (int loc = 0; loc < group_size; ++loc) {
      int k = current_pos + loc;
      operators[k] = (e & (1LL << loc)) ? 1 : 0;
    }
    current_pos += group_size;
  }
  cout << "!";
  for (int k = 1; k <= n; ++k) {
    cout << " " << operators[k];
  }
  cout << "\n";
  cout.flush();
  return 0;
}