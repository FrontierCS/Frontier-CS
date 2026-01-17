#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

vector<ll> get_divisors(ll n) {
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

ll mygcd(ll a, ll b) { return b == 0 ? a : mygcd(b, a % b); }

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  for (int test = 0; test < n; test++) {
    cout << "? 1 1" << endl;
    cout.flush();
    int u;
    cin >> u;
    const int B = 500;
    map<int, int> baby;
    int current = u;
    baby[current] = 0;
    int S = -1;
    bool found_small = false;
    for (int i = 1; i <= B; i++) {
      cout << "? " << current << " 1" << endl;
      cout.flush();
      int nxt;
      cin >> nxt;
      current = nxt;
      if (current == u) {
        S = i;
        found_small = true;
        break;
      }
      baby[current] = i;
    }
    if (found_small) {
      cout << "! " << S << endl;
      cout.flush();
      int ver;
      cin >> ver;
      if (ver == -1) return 0;
      continue;
    }
    baby[current] = B;
    ll g = 0;
    vector<int> stepsizes = {B, B + 1, B + 2};
    for (int bs : stepsizes) {
      for (int j = 1; j <= bs; j++) {
        ll stp = (ll)j * bs;
        if (stp > 5000000000000000000LL) continue;
        cout << "? " << u << " " << stp << endl;
        cout.flush();
        int posj;
        cin >> posj;
        if (baby.count(posj)) {
          int r = baby[posj];
          ll diff = stp - r;
          if (diff <= 0) continue;
          if (g == 0) {
            g = diff;
          } else {
            g = mygcd(g, diff);
          }
        }
      }
    }
    vector<ll> divs = get_divisors(g);
    S = -1;
    for (auto sll : divs) {
      ll s = sll;
      if (s < 3 || s > 1000000) continue;
      cout << "? " << u << " " << s << endl;
      cout.flush();
      int res;
      cin >> res;
      if (res == u) {
        S = (int)s;
        break;
      }
    }
    cout << "! " << S << endl;
    cout.flush();
    int ver;
    cin >> ver;
    if (ver == -1) return 0;
  }
  return 0;
}