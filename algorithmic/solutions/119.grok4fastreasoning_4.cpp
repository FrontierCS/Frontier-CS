#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1000000007LL;
const int BS = 20;
const int MAXU = 601;

ll modinv(ll a, ll m = MOD) {
  ll m0 = m, t, q;
  ll x0 = 0, x1 = 1;
  if (m == 1) return 0;
  while (a > 1) {
    q = a / m;
    t = m;
    m = a % m, a = t;
    t = x0;
    x0 = x1 - q * x0;
    x1 = t;
  }
  if (x1 < 0) x1 += m0;
  return x1;
}

ll simulate(ll init, int mask, const vector<ll>& b, int len) {
  ll cur = init % MOD;
  for (int i = 1; i <= len; ++i) {
    int op = (mask & (1 << (i - 1))) ? 1 : 0;
    ll na = b[i];
    if (op == 0) {
      cur = (cur + na) % MOD;
    } else {
      cur = cur * na % MOD;
    }
  }
  return cur;
}

vector<ll> generate_b(int l, int len, int qnum) {
  vector<ll> b(len + 1);
  ll sd = (ll)l * 10007LL + (ll)qnum * 10009LL + 12345LL;
  for (int i = 1; i <= len; ++i) {
    sd = (sd * 1103515245LL + 12345LL) % MOD;
    b[i] = (sd % (MOD - 1)) + 1;
  }
  return b;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<int> operators(n + 1, -1);
  int pos = n;
  while (pos >= 1) {
    int l = max(1, pos - BS + 1);
    int r = pos;
    int len = r - l + 1;
    ll C = 0;
    for (int j = r + 1; j <= n; ++j) {
      if (operators[j] == 0) ++C;
    }
    // first query
    vector<ll> b = generate_b(l, len, 0);
    vector<ll> a(n + 1, 1LL);
    for (int i = 1; i <= len; ++i) {
      a[l + i - 1] = b[i];
    }
    cout << "?";
    for (int i = 0; i <= n; ++i) {
      cout << " " << a[i];
    }
    cout << "\n";
    cout.flush();
    ll R;
    cin >> R;
    ll target = (R - C + MOD) % MOD;
    vector<int> cands;
    for (int msk = 0; msk < (1 << len); ++msk) {
      ll t = simulate(0LL, msk, b, len);
      ll oneh = simulate(1LL, msk, b, len);
      ll q = (oneh - t + MOD) % MOD;
      bool fit = false;
      if (q == 0) {
        if (t == target) fit = true;
      } else {
        ll num = (target - t + MOD) % MOD;
        ll invq = modinv(q);
        ll uc = num * invq % MOD;
        if (uc >= 1 && uc <= MAXU) fit = true;
      }
      if (fit) cands.push_back(msk);
    }
    int the_mask;
    if (cands.size() == 1) {
      the_mask = cands[0];
    } else {
      // second query
      vector<ll> b2 = generate_b(l, len, 1);
      vector<ll> a2(n + 1, 1LL);
      for (int i = 1; i <= len; ++i) {
        a2[l + i - 1] = b2[i];
      }
      cout << "?";
      for (int i = 0; i <= n; ++i) {
        cout << " " << a2[i];
      }
      cout << "\n";
      cout.flush();
      ll R2;
      cin >> R2;
      ll target2 = (R2 - C + MOD) % MOD;
      vector<int> newcands;
      for (int msk : cands) {
        ll t = simulate(0LL, msk, b2, len);
        ll oneh = simulate(1LL, msk, b2, len);
        ll q = (oneh - t + MOD) % MOD;
        bool fit = false;
        if (q == 0) {
          if (t == target2) fit = true;
        } else {
          ll num = (target2 - t + MOD) % MOD;
          ll invq = modinv(q);
          ll uc = num * invq % MOD;
          if (uc >= 1 && uc <= MAXU) fit = true;
        }
        if (fit) newcands.push_back(msk);
      }
      assert(newcands.size() == 1);
      the_mask = newcands[0];
    }
    for (int ii = 0; ii < len; ++ii) {
      int opi = (the_mask & (1 << ii)) ? 1 : 0;
      operators[l + ii] = opi;
    }
    pos = l - 1;
  }
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << operators[i];
  }
  cout << "\n";
  cout.flush();
  return 0;
}