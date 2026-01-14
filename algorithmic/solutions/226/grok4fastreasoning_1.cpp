#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

ll path_max(const vector<ll>& w, int st, int en) {
  if (st > en) return 0;
  ll prev_no = 0;
  ll prev_yes = LLONG_MIN / 2;
  for (int i = st; i <= en; ++i) {
    ll curr_no = max(prev_no, prev_yes);
    ll curr_yes = w[i] + prev_no;
    prev_no = curr_no;
    prev_yes = curr_yes;
  }
  return max(prev_no, prev_yes);
}

int main() {
  ll n, x, y;
  cin >> n >> x >> y;
  ll g = __gcd(x, y);
  ll p = x + y;
  vector<ll> cnt(p + 1, 0);
  for (ll r = 1; r <= p; ++r) {
    if (r > n) cnt[r] = 0;
    else cnt[r] = (n - r) / p + 1;
  }
  vector<bool> visited(p, false);
  ll total = 0;
  for (ll start = 0; start < p; ++start) {
    if (visited[start]) continue;
    vector<int> cycle;
    ll cur = start;
    while (!visited[cur]) {
      visited[cur] = true;
      cycle.push_back(cur);
      cur = (cur + x) % p;
    }
    int ll_ = cycle.size();
    vector<ll> weights(ll_);
    for (int j = 0; j < ll_; ++j) {
      int res = cycle[j];
      weights[j] = (res == 0 ? cnt[p] : cnt[res]);
    }
    ll c1 = path_max(weights, 1, ll_ - 1);
    ll c2 = weights[0] + path_max(weights, 2, ll_ - 2);
    total += max(c1, c2);
  }
  cout << total << endl;
  return 0;
}