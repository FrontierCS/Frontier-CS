#include <bits/stdc++.h>
using namespace std;

using ll = long long;

ll mul_mod(ll x, ll y, ll mod) {
  return ((__int128)x * y) % mod;
}

int bitlen(ll x) {
  if (x == 0) return 0;
  return 64 - __builtin_clzll(x);
}

ll compute_S(ll n, ll a0) {
  ll sum = 0;
  ll cur = a0 % n;
  if (cur < 0) cur += n;
  for (int i = 0; i < 60; i++) {
    ll bt = bitlen(cur);
    ll bb = bt + 1;
    sum += bb * bb;
    cur = mul_mod(cur, cur, n);
  }
  return sum;
}

vector<ll> get_b(ll n, ll a0) {
  vector<ll> bb(60);
  ll cur = a0 % n;
  if (cur < 0) cur += n;
  for (int i = 0; i < 60; i++) {
    bb[i] = bitlen(cur) + 1;
    cur = mul_mod(cur, cur, n);
  }
  return bb;
}

ll compute_contrib(ll a0, ll mask, ll n) {
  ll cl = 0;
  ll tr = 1;
  ll ta = a0 % n;
  if (ta < 0) ta += n;
  for (int i = 0; i < 6; i++) {
    ll ba = bitlen(ta) + 1;
    if (mask & (1LL << i)) {
      ll br = bitlen(tr) + 1;
      cl += br * ba;
      tr = mul_mod(tr, ta, n);
    }
    ta = mul_mod(ta, ta, n);
  }
  return cl;
}

bool find_subset(int pos, int need, ll rem, const vector<pair<ll, int>>& hb, vector<int>& sel) {
  if (need == 0) {
    return rem == 0;
  }
  if (pos == (int)hb.size()) return false;
  int rpos = hb.size() - pos;
  if (need > rpos) return false;
  ll maxp = 0;
  for (int j = pos; j < (int)hb.size(); j++) maxp += hb[j].first;
  if (maxp < rem) return false;
  // skip
  if (find_subset(pos + 1, need, rem, hb, sel)) return true;
  // take
  ll bb = hb[pos].first;
  if (bb <= rem && need >= 1) {
    sel.push_back(hb[pos].second);
    if (find_subset(pos + 1, need - 1, rem - bb, hb, sel)) return true;
    sel.pop_back();
  }
  return false;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  ll n;
  cin >> n;
  // query a=1 for h
  cout << "? 1" << endl;
  ll t1;
  cin >> t1;
  ll s1 = compute_S(n, 1);
  ll e1 = t1 - s1;
  ll h = e1 / 4;
  // query a=2
  ll a_two = 2;
  cout << "? " << a_two << endl;
  ll t2;
  cin >> t2;
  ll s2 = compute_S(n, a_two);
  ll e2 = t2 - s2;
  auto b = get_b(n, a_two);
  ll bfull = bitlen(n - 1) + 1;
  vector<ll> high_b;
  for (int i = 6; i < 60; i++) high_b.push_back(b[i]);
  const int MAXS = 3701;
  bitset<MAXS> poss[55];
  poss[0][0] = 1;
  for (auto bbv : high_b) {
    ll bb = bbv;
    for (int kk = 54; kk >= 1; kk--) {
      poss[kk] |= (poss[kk - 1] << bb);
    }
  }
  vector<ll> cand_low;
  for (int m = 1; m < 64; m += 2) {
    ll cl = compute_contrib(a_two, m, n);
    ll eh = e2 - cl;
    if (eh >= 0 && bfull > 0 && eh % bfull == 0) {
      ll sh = eh / bfull;
      int pl = __builtin_popcount(m);
      int hg = h - pl;
      if (hg >= 0 && hg <= 54 && sh < MAXS && poss[hg][sh]) {
        cand_low.push_back(m);
      }
    }
  }
  ll loww = -1;
  if (cand_low.size() == 1) {
    loww = cand_low[0];
  } else {
    // second query a=3
    ll a_three = 3;
    cout << "? " << a_three << endl;
    ll t3;
    cin >> t3;
    ll s3 = compute_S(n, a_three);
    ll e3 = t3 - s3;
    auto b3 = get_b(n, a_three);
    vector<ll> high_b3;
    for (int i = 6; i < 60; i++) high_b3.push_back(b3[i]);
    bitset<MAXS> poss3[55];
    poss3[0][0] = 1;
    for (auto bbv : high_b3) {
      ll bb = bbv;
      for (int kk = 54; kk >= 1; kk--) {
        poss3[kk] |= (poss3[kk - 1] << bb);
      }
    }
    vector<ll> cand2;
    for (auto m : cand_low) {
      ll cl3 = compute_contrib(a_three, m, n);
      ll eh3 = e3 - cl3;
      if (eh3 >= 0 && bfull > 0 && eh3 % bfull == 0) {
        ll sh3 = eh3 / bfull;
        int pl = __builtin_popcount(m);
        int hg = h - pl;
        if (hg >= 0 && hg <= 54 && sh3 < MAXS && poss3[hg][sh3]) {
          cand2.push_back(m);
        }
      }
    }
    if (cand2.size() == 1) {
      loww = cand2[0];
    } else {
      // assume 1, take first
      if (!cand2.empty()) loww = cand2[0];
    }
  }
  if (loww == -1) {
    // error
    cout << "! 0" << endl;
    return 0;
  }
  ll low = loww;
  int pl = __builtin_popcount(low);
  int hg = h - pl;
  ll cl = compute_contrib(a_two, low, n);
  ll eh = e2 - cl;
  ll sh = eh / bfull;
  // backtrack
  vector<pair<ll, int>> high_pairs;
  for (int i = 6; i < 60; i++) {
    high_pairs.emplace_back(b[i], i);
  }
  sort(high_pairs.rbegin(), high_pairs.rend());
  vector<int> sel;
  bool found = find_subset(0, hg, sh, high_pairs, sel);
  if (!found) {
    // error
    cout << "! 0" << endl;
    return 0;
  }
  ll hm = 0;
  for (int p : sel) hm |= (1LL << p);
  ll dd = low + (hm << 6);
  cout << "! " << dd << endl;
  return 0;
}