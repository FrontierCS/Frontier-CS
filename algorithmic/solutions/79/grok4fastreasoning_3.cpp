#include <bits/stdc++.h>
using namespace std;
using ull = unsigned long long;

ull mulmod(ull a, ull b, ull m) {
  return (__int128)a * b % m;
}

ull mod_pow(ull a, ull b, ull m) {
  ull res = 1;
  a %= m;
  while (b) {
    if (b & 1) res = mulmod(res, a, m);
    a = mulmod(a, a, m);
    b >>= 1;
  }
  return res;
}

pair<ull, ull> tonelli_shanks(ull n, ull p) {
  n %= p;
  if (n == 0) return {0, 0};
  if (mod_pow(n, (p - 1) / 2, p) != 1) return {0, 0};
  if (p % 4 == 3) {
    ull r = mod_pow(n, (p + 1) / 4, p);
    return {r, p - r};
  }
  ull q = p - 1;
  int s = 0;
  while (q % 2 == 0) {
    q /= 2;
    s++;
  }
  ull z = 2;
  while (mod_pow(z, (p - 1) / 2, p) != p - 1) z++;
  ull m = s;
  ull c = mod_pow(z, q, p);
  ull t = mod_pow(n, q, p);
  ull r = mod_pow(n, (q + 1) / 2, p);
  while (true) {
    if (t == 0) return {0, 0};
    if (t == 1) return {r, p - r};
    int i = 1;
    ull t2i = mulmod(t, t, p);
    for (i = 1; i < m; i++) {
      if (t2i == 1) break;
      t2i = mulmod(t2i, t2i, p);
    }
    if (i == m) return {0, 0};
    ull b = mod_pow(c, 1ULL << (m - i - 1), p);
    r = mulmod(r, b, p);
    c = mulmod(b, b, p);
    t = mulmod(t, c, p);
    m = i;
  }
}

ull mod_inverse(ull a, ull m) {
  ull m0 = m;
  long long y = 0, x = 1;
  if (m == 1) return 0;
  while (a > 1) {
    ull q = a / m;
    ull t = m;
    m = a % m;
    a = t;
    t = y;
    y = x - q * y;
    x = t;
  }
  if (x < 0) x += m0;
  return x;
}

ull crt(ull a1, ull m1, ull a2, ull m2) {
  ull inv = mod_inverse(m1 % m2, m2);
  ull u = mulmod((a2 + m2 - a1 % m2) % m2, inv, m2);
  return a1 + u * m1;
}

int get_bits(ull x) {
  if (x == 0) return 0;
  return 64 - __builtin_clzll(x);
}

ull find_factor(ull n) {
  if (n % 2 == 0) return 2;
  for (ull i = 3; i * i <= n; i += 2) {
    if (n % i == 0) return i;
  }
  return n;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  cout.tie(nullptr);
  ull n;
  cin >> n;
  cout << "? 1" << '\n';
  cout.flush();
  ull T1;
  cin >> T1;
  ull S1 = 60ULL * 4ULL;
  ull total_w = (T1 - S1) / 4ULL;
  ull pp = find_factor(n);
  ull qq = n / pp;
  if (pp > qq) swap(pp, qq);
  ull dd = 0ULL;
  ull curr_e = 0ULL;
  ull curr_wt = 0ULL;
  for (int kk = 0; kk < 60; ++kk) {
    bool poss = true;
    ull base_p;
    {
      ull curr = pp - 1ULL;
      for (int jj = 0; jj < kk; ++jj) {
        auto rt = tonelli_shanks(curr, pp);
        if (rt.first == 0ULL) {
          poss = false;
          break;
        }
        curr = rt.first;
      }
      if (!poss) {
        // set to 0
        continue;
      }
      base_p = curr;
    }
    ull base_q;
    {
      ull curr = qq - 1ULL;
      for (int jj = 0; jj < kk; ++jj) {
        auto rt = tonelli_shanks(curr, qq);
        if (rt.first == 0ULL) {
          poss = false;
          break;
        }
        curr = rt.first;
      }
      if (!poss) {
        continue;
      }
      base_q = curr;
    }
    if (!poss) continue;
    ull basee = crt(base_p, pp, base_q, qq);
    // compute A and b
    vector<ull> AA(61);
    vector<int> bb(61);
    AA[0] = basee % n;
    bb[0] = get_bits(AA[0]) + 1;
    ull SS = (ull)bb[0] * bb[0];
    for (int ii = 0; ii < 60; ++ii) {
      AA[ii + 1] = mulmod(AA[ii], AA[ii], n);
      bb[ii + 1] = get_bits(AA[ii + 1]) + 1;
      SS += (ull)bb[ii + 1] * bb[ii + 1];
    }
    cout << "? " << basee << '\n';
    cout.flush();
    ull TT;
    cin >> TT;
    ull EE = TT - SS;
    // simulate low
    ull rr = 1ULL;
    ull aa = basee % n;
    ull e_loww = 0ULL;
    for (int jj = 0; jj < kk; ++jj) {
      int bt = (curr_e >> jj) & 1;
      int bbb = get_bits(aa) + 1;
      if (bt) {
        int ccc = get_bits(rr) + 1;
        e_loww += (ull)ccc * bbb;
        rr = mulmod(rr, aa, n);
      }
      aa = mulmod(aa, aa, n);
    }
    ull Rkk = rr;
    ull E_low = e_loww;
    int crr = get_bits(Rkk) + 1;
    int bkk = bb[kk];
    ull extra_kk = (ull)crr * bkk;
    int c00 = crr;
    ull rh00 = Rkk;
    ull rh11 = mulmod(Rkk, AA[kk], n);
    int c11 = get_bits(rh11) + 1;
    ull wh00 = total_w - curr_wt;
    ull wh11 = total_w - curr_wt - 1ULL;
    ull cost_per00 = (ull)c00 * 2ULL;
    ull cost_per11 = (ull)c11 * 2ULL;
    ull exp00 = wh00 * cost_per00;
    ull exp11 = extra_kk + wh11 * cost_per11;
    ull obs = EE - E_low;
    bool bitkk = false;
    if (obs == exp00) {
      bitkk = false;
    } else if (obs == exp11) {
      bitkk = true;
    } else {
      // mismatch, assume 0
      bitkk = false;
    }
    if (bitkk) {
      dd |= (1ULL << kk);
      ++curr_wt;
    }
    curr_e |= (ull)bitkk << kk;
  }
  cout << "! " << dd << '\n';
  cout.flush();
  return 0;
}