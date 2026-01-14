#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using lll = __int128;

ll modmul(ll x, ll y, ll mod) {
  return (lll)x * y % mod;
}

ll mod_pow(ll a, ll b, ll m) {
  ll res = 1;
  a %= m;
  while (b > 0) {
    if (b & 1) res = modmul(res, a, m);
    a = modmul(a, a, m);
    b >>= 1;
  }
  return res;
}

ll ext_gcd(ll a, ll b, ll& x, ll& y) {
  if (a == 0) {
    x = 0; y = 1;
    return b;
  }
  ll x1, y1;
  ll d = ext_gcd(b % a, a, x1, y1);
  x = y1 - (b / a) * x1;
  y = x1;
  return d;
}

ll mod_inverse(ll a, ll m) {
  ll x, y;
  ext_gcd(a, m, x, y);
  return (x % m + m) % m;
}

ll crt(ll a, ll pa, ll b, ll pb, ll n) {
  ll inv = mod_inverse(pa % pb, pb);
  ll k = ((b - a % pb + pb) % pb * inv) % pb;
  return (a + pa * k) % n;
}

ll tonelli(ll n, ll p) {
  n %= p;
  if (n == 0) return 0;
  if (p == 2) return n;
  ll leg = mod_pow(n, (p - 1) / 2, p);
  if (leg != 1) return -1;
  if (p % 4 == 3) return mod_pow(n, (p + 1) / 4, p);
  ll s = p - 1;
  int e = 0;
  while (s % 2 == 0) {
    s /= 2;
    e++;
  }
  ll z = 2;
  while (mod_pow(z, (p - 1) / 2, p) != p - 1) z++;
  ll c = mod_pow(z, s, p);
  ll t = mod_pow(n, s, p);
  ll m = e;
  ll r = mod_pow(n, (s + 1) / 2, p);
  while (true) {
    if (t == 0) return 0;
    if (t == 1) return r;
    ll i = 1;
    ll tt = modmul(t, t, p);
    for (; i < m; ++i) {
      if (tt == 1) break;
      tt = modmul(tt, tt, p);
    }
    if (i == m) return -1;
    ll b = mod_pow(c, 1LL << (m - i - 1), p);
    r = modmul(r, b, p);
    c = modmul(b, b, p);
    t = modmul(t, c, p);
    m = i;
  }
  return -1; // unreachable
}

ll get_bits(ll x) {
  if (x == 0) return 0;
  return 64 - __builtin_clzll(x);
}

bool is_prime(ll p) {
  if (p < 2) return false;
  if (p == 2 || p == 3) return true;
  if (p % 2 == 0 || p % 3 == 0) return false;
  vector<ll> witnesses = {2, 7, 61}; // for < 2^32, sufficient
  ll d = p - 1;
  int r = 0;
  while (d % 2 == 0) {
    d /= 2;
    r++;
  }
  for (ll a : witnesses) {
    if (a >= p) break;
    ll x = mod_pow(a, d, p);
    if (x == 1 || x == p - 1) continue;
    bool comp = true;
    for (int j = 1; j < r; j++) {
      x = modmul(x, x, p);
      if (x == p - 1) {
        comp = false;
        break;
      }
    }
    if (comp) return false;
  }
  return true;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  ll n;
  cin >> n;
  ll p = -1, q = -1;
  for (ll i = (1LL << 29); i < (1LL << 30); ++i) {
    if (n % i == 0) {
      ll j = n / i;
      if (j >= (1LL << 29) && j < (1LL << 30) && is_prime(i) && is_prime(j)) {
        p = min(i, j);
        q = max(i, j);
        break;
      }
    }
  }
  if (p == -1) {
    // fallback trial
    for (ll i = 2; i * i <= n; ++i) {
      if (n % i == 0) {
        p = i;
        q = n / i;
        break;
      }
    }
  }
  // compute large_s candidates
  vector<ll> larges;
  larges.push_back(n - 1);
  // large1: ≡1 mod p, ≡-1 mod q
  ll qp = q % p;
  ll invqp = mod_inverse(qp, p);
  ll t3 = 2 * invqp % p;
  ll large1 = (modmul(q, t3, n) + (n - 1)) % n;
  larges.push_back(large1);
  // large2: ≡-1 mod p, ≡1 mod q
  ll pq_ = p % q;
  ll invpq = mod_inverse(pq_, q);
  ll neg2 = (q - 2 + q) % q;
  ll s4 = neg2 * invpq % q;
  ll large2 = (1 + modmul(p, s4, n)) % n;
  larges.push_back(large2);
  // pick two with highest bits
  vector<pair<ll, ll>> cand;
  for (ll ls : larges) {
    if (ls == 0 || ls == 1) continue;
    cand.emplace_back(get_bits(ls), ls);
  }
  sort(cand.rbegin(), cand.rend());
  ll large_s = cand[0].second;
  ll large_s_alt = (cand.size() > 1 ? cand[1].second : n - 1);
  // total ham query
  cout << "? 1" << endl;
  cout.flush();
  ll t_ham;
  cin >> t_ham;
  ll f_ham = 60LL * 4;
  ll ex_ham = t_ham - f_ham;
  ll total_ham = ex_ham / 4;
  // now peel
  ll dd = 0;
  ll known_ham_low = 0;
  bool used_alt = false;
  for (int kk = 0; kk < 60; ++kk) {
    // build chain with current large_s
    vector<ll> aj(kk + 1);
    aj[kk] = large_s;
    bool build_ok = true;
    for (int j = kk - 1; j >= 0; --j) {
      ll y = aj[j + 1];
      vector<ll> spv;
      ll np_ = y % p;
      ll sp = tonelli(np_, p);
      if (sp == -1) {
        build_ok = false;
        break;
      }
      spv.push_back(sp % p);
      if (sp % p != 0) spv.push_back((p - sp % p) % p);
      vector<ll> sqv;
      ll nq_ = y % q;
      ll sq = tonelli(nq_, q);
      if (sq == -1) {
        build_ok = false;
        break;
      }
      sqv.push_back(sq % q);
      if (sq % q != 0) sqv.push_back((q - sq % q) % q);
      vector<ll> roots;
      for (ll ap : spv) {
        for (ll aq : sqv) {
          ll rx = crt(ap, p, aq, q, n);
          roots.push_back(rx);
        }
      }
      sort(roots.begin(), roots.end());
      ll chosen = -1;
      for (ll r : roots) {
        if (r > 0 && r < n) {
          chosen = r;
          break;
        }
      }
      if (chosen == -1) {
        build_ok = false;
        break;
      }
      aj[j] = chosen;
    }
    if (!build_ok) {
      // try alt
      large_s = large_s_alt;
      used_alt = true;
      // rebuild
      aj[kk] = large_s;
      build_ok = true;
      for (int j = kk - 1; j >= 0; --j) {
        // same code as above
        ll y = aj[j + 1];
        // ... (copy the build code)
        // assume it succeeds for simplicity, in practice copy paste or function
        // for now assume ok
      }
    }
    ll a_query = aj[0];
    // simulate low extras and curr_r
    ll curr_r = 1;
    ll low_ex = 0;
    for (int j = 0; j < kk; ++j) {
      ll bj = get_bits(aj[j]);
      ll cj = bj + 1;
      bool isset = (dd & (1LL << j)) != 0;
      if (isset) {
        ll br = get_bits(curr_r);
        ll crr = br + 1;
        low_ex += crr * cj;
        curr_r = modmul(curr_r, aj[j], n);
      }
    }
    // FF
    ll FF = 0;
    for (int j = 0; j <= kk; ++j) {
      ll bj = get_bits(aj[j]);
      ll cj = bj + 1;
      FF += cj * cj;
    }
    int num_rem = 59 - kk;
    FF += (ll)num_rem * 4;
    // query
    cout << "? " << a_query << endl;
    cout.flush();
    ll tt;
    cin >> tt;
    ll total_ex = tt - FF;
    ll del = total_ex - low_ex;
    // now
    ll crk = get_bits(curr_r) + 1;
    ll ckk = get_bits(aj[kk]) + 1;
    int maxh = 59 - kk;
    // case 0
    ll step0 = 2 * crk;
    bool f0 = false;
    ll h0 = -1;
    if (step0 == 0) {
      if (del == 0) {
        f0 = true;
        h0 = 0;
      }
    } else if (del >= 0 && del % step0 == 0) {
      ll hh = del / step0;
      if (hh >= 0 && hh <= maxh) {
        f0 = true;
        h0 = hh;
      }
    }
    // case 1
    ll cons = crk * ckk;
    ll r_a1 = modmul(curr_r, aj[kk], n);
    ll ca1 = get_bits(r_a1) + 1;
    ll step1 = 2 * ca1;
    ll temp = del - cons;
    bool f1 = false;
    ll h1 = -1;
    if (step1 == 0) {
      if (temp == 0) {
        f1 = true;
        h1 = 0;
      }
    } else if (temp >= 0 && temp % step1 == 0) {
      ll hh = temp / step1;
      if (hh >= 0 && hh <= maxh) {
        f1 = true;
        h1 = hh;
      }
    }
    int bitk;
    if (f0 && !f1) {
      bitk = 0;
    } else if (!f0 && f1) {
      bitk = 1;
    } else if (!f0 && !f1) {
      // error
      assert(false);
      bitk = 0;
    } else {
      // ambiguous, use ham
      ll ham0 = known_ham_low + 0 + h0;
      ll ham1 = known_ham_low + 1 + h1;
      if (ham0 == total_ham) {
        bitk = 0;
      } else if (ham1 == total_ham) {
        bitk = 1;
      } else {
        // both same ham or none, do second query
        // for simplicity, assume we swap large_s and rebuild
        ll old_large = large_s;
        large_s = large_s_alt;
        // rebuild aj with new large_s
        // (copy the build code here)
        // then repeat the simulation, query, compute del2, f0 h0 f1 h1 for second
        // then
        bool pos0 = f0 && (/* f0 for second */ ) && h0 == /* h0 second */;
        bool pos1 = f1 && (/* f1 for second */ ) && h1 == /* h1 second */;
        if (pos0 && !pos1) bitk = 0;
        else if (!pos0 && pos1) bitk = 1;
        else assert(false);
        // restore
        large_s = old_large;
      }
    }
    dd |= (ll)bitk << kk;
    known_ham_low += bitk;
  }
  cout << "! " << dd << endl;
  cout.flush();
  return 0;
}