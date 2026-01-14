#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int query(int v, ll x) {
  cout << "? " << v << " " << x << endl;
  cout.flush();
  int r;
  cin >> r;
  return r;
}

vector<ll> get_divs(ll n) {
  vector<ll> d;
  for (ll i = 1; i * i <= n; i++) {
    if (n % i == 0) {
      d.push_back(i);
      if (i != n / i) d.push_back(n / i);
    }
  }
  sort(d.begin(), d.end());
  return d;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  const int MAXV = 1000000;
  const int M = 1000;
  vector<ll> step_of(MAXV + 1);
  for (int cas = 0; cas < n; cas++) {
    fill(step_of.begin(), step_of.end(), -1LL);
    int c = query(1, 1LL);
    step_of[c] = 0;
    ll s = -1;
    bool early = false;
    for (int i = 1; i < M; i++) {
      int nv = query(c, (ll)i);
      if (nv == c) {
        s = i;
        early = true;
        break;
      }
      if (step_of[nv] != -1) {
        s = i - step_of[nv];
        early = true;
        break;
      }
      step_of[nv] = i;
    }
    if (!early) {
      ll steps = 0;
      int currv = c;
      ll tt = -1;
      for (int j = 1; j <= M + 10; j++) {
        int nv = query(currv, (ll)M);
        steps += M;
        if (step_of[nv] != -1) {
          tt = steps - step_of[nv];
          break;
        }
        step_of[nv] = steps;
        currv = nv;
      }
      auto divs = get_divs(tt);
      s = -1;
      for (auto d : divs) {
        if (d < 3 || d > MAXV) continue;
        int resv = query(c, d);
        if (resv == c) {
          s = d;
          break;
        }
      }
    }
    cout << "! " << s << endl;
    cout.flush();
    int ver;
    cin >> ver;
    if (ver == -1) return 0;
  }
  return 0;
}