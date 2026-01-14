#include <bits/stdc++.h>
using namespace std;

typedef long long ll;
typedef unsigned long long ull;

int get_bits(ull x) {
  if (x == 0) return 0;
  return 64 - __builtin_clzll(x);
}

ull mod_mul(ull x, ull y, ull mod) {
  return (__int128)x * y % mod;
}

int main() {
  srand(time(NULL));
  ios::sync_with_stdio(false);
  cin.tie(0);
  ull n;
  cin >> n;
  // Query a=1 to get wt
  cout << "? 1" << endl;
  ll time1;
  cin >> time1;
  ll fixed1 = 60LL * 4LL;
  ll var1 = time1 - fixed1;
  ll wt = var1 / 4LL;
  ull d = 1ULL; // bit 0 set
  ll rem_wt = wt - 1;
  for (int l = 1; l < 60; ++l) {
    ull a;
    vector<int> b(60);
    bool good = false;
    while (!good) {
      ull r1 = ((ull)rand() << 30) ^ rand();
      a = r1 % n;
      if (a == 0) continue;
      ull cur = a % n;
      b[0] = get_bits(cur);
      for (int i = 0; i < 59; ++i) {
        cur = mod_mul(cur, cur, n);
        b[i + 1] = get_bits(cur);
      }
      if (b[l] >= 58) good = true;
    }
    // Query
    cout << "? " << a << endl;
    ll tm;
    cin >> tm;
    // Fixed
    ll fx = 0;
    for (int i = 0; i < 60; ++i) fx += (ll)(b[i] + 1) * (b[i] + 1);
    // Simulate low l
    ull rr = 1ULL;
    ull cura = a % n;
    ll lowex = 0;
    for (int i = 0; i < l; ++i) {
      if (d & (1ULL << i)) {
        int brr = get_bits(rr);
        int baa = get_bits(cura);
        lowex += (ll)(brr + 1) * (baa + 1);
        rr = mod_mul(rr, cura, n);
      }
      cura = mod_mul(cura, cura, n);
    }
    int brl = get_bits(rr);
    int blv = b[l];
    ll Lv = (ll)(brl + 1) * (blv + 1);
    ll vh = tm - fx - lowex;
    // Avg for higher i > l
    double smav = 0.0;
    int nhh = 60 - l - 1;
    if (nhh > 0) {
      for (int i = l + 1; i < 60; ++i) smav += (b[i] + 1.0);
      smav /= nhh;
    }
    double avgwv = 61.0 * smav;
    double p0 = (double)rem_wt * avgwv;
    double p1 = (double)Lv + (double)(rem_wt - 1) * avgwv;
    double df0 = fabs((double)vh - p0);
    double df1 = fabs((double)vh - p1);
    int bt = (df0 < df1) ? 0 : 1;
    if (bt) d |= (1ULL << l);
    rem_wt -= bt;
  }
  cout << "! " << d << endl;
  return 0;
}