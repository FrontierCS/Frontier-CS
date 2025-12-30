#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

ll compute_num_pm(const vector<vector<int>>& adj, int k) {
  int n = 1 << k;
  vector<ll> dp(n, 0LL);
  dp[0] = 1;
  for (int r = 0; r < k; ++r) {
    vector<ll> ndp(n, 0LL);
    for (int m = 0; m < n; ++m) {
      if (dp[m] == 0) continue;
      int pc = __builtin_popcount(m);
      if (pc != r) continue;
      for (int j : adj[r]) {
        if ((m & (1 << j)) == 0) {
          int nm = m | (1 << j);
          ndp[nm] += dp[m];
        }
      }
    }
    dp = std::move(ndp);
  }
  return dp[n - 1];
}

vector<int> find_matching(int r, int mask, const vector<vector<int>>& adj, int k) {
  if (r == k) {
    return {};
  }
  for (int j : adj[r]) {
    if ((mask & (1 << j)) == 0) {
      vector<int> sub = find_matching(r + 1, mask | (1 << j), adj, k);
      if ((int)sub.size() == k - r - 1) {
        sub.insert(sub.begin(), j);
        return sub;
      }
    }
  }
  return {-1};
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  ll B;
  int k, w;
  cin >> B >> k >> w;
  vector<ll> fact(21, 1LL);
  for (int i = 1; i <= 20; ++i) {
    fact[i] = fact[i - 1] * (ll)i;
  }
  // Probe for uu (x + y)
  cout << "? 1 " << -B << " " << -B << endl;
  cout.flush();
  vector<ll> du(k);
  for (auto& x : du) cin >> x;
  vector<ll> uu(k);
  for (int i = 0; i < k; ++i) {
    uu[i] = du[i] - 2 * B;
  }
  // Probe for vv (x - y)
  cout << "? 1 " << -B << " " << B << endl;
  cout.flush();
  vector<ll> dv(k);
  for (auto& x : dv) cin >> x;
  vector<ll> vv(k);
  for (int i = 0; i < k; ++i) {
    vv[i] = dv[i] - 2 * B;
  }
  // Compute expected
  map<ll, int> u_cnt;
  for (ll val : uu) ++u_cnt[val];
  ll expect = 1LL;
  for (auto& p : u_cnt) {
    int sz = p.second;
    expect *= fact[sz];
  }
  // Initial adj
  vector<vector<int>> adj(k);
  for (int i = 0; i < k; ++i) {
    for (int j = 0; j < k; ++j) {
      ll uval = uu[i], vval = vv[j];
      if ((uval + vval) % 2 != 0) continue;
      ll xval = (uval + vval) / 2;
      ll yval = (uval - vval) / 2;
      if (abs(xval) > B || abs(yval) > B) continue;
      adj[i].push_back(j);
    }
  }
  int waves = 2;
  ll step = 20000000LL;
  for (int qid = 0; qid < 100 && waves < w; ++qid) {
    ll numm = compute_num_pm(adj, k);
    if (numm > 0 && (numm == 1 || numm == expect)) {
      vector<int> pairing = find_matching(0, 0, adj, k);
      cout << "!";
      for (int i = 0; i < k; ++i) {
        int j = pairing[i];
        ll x = (uu[i] + vv[j]) / 2;
        ll y = (uu[i] - vv[j]) / 2;
        cout << " " << x << " " << y;
      }
      cout << endl;
      cout.flush();
      return 0;
    }
    // New query
    ll uss = 0;
    ll vss = -2 * B + (ll)qid * step;
    if (abs(vss) > 2 * B) vss = -2 * B + (vss + 2 * B) % (4 * B + 1);
    // Same parity
    ll paru = llabs(uss % 2);
    ll parv = llabs(vss % 2);
    if (paru != parv) vss -= 1;
    ll ss = (uss + vss) / 2;
    ll tt = (uss - vss) / 2;
    if (abs(ss) > B || abs(tt) > B) {
      vss += 2;
      ss = (uss + vss) / 2;
      tt = (uss - vss) / 2;
      if (abs(ss) > B || abs(tt) > B) continue;
    }
    cout << "? 1 " << ss << " " << tt << endl;
    cout.flush();
    vector<ll> ddd(k);
    for (auto& x : ddd) cin >> x;
    // Filter
    vector<vector<int>> new_adj(k);
    for (int i = 0; i < k; ++i) {
      for (int j : adj[i]) {
        ll dist_val = max(abs(uu[i] - uss), abs(vv[j] - vss));
        auto it = lower_bound(ddd.begin(), ddd.end(), dist_val);
        if (it != ddd.end() && *it == dist_val) {
          new_adj[i].push_back(j);
        }
      }
    }
    adj = std::move(new_adj);
    ++waves;
  }
  // If not resolved, pick any from current adj
  vector<int> pairing = find_matching(0, 0, adj, k);
  cout << "!";
  for (int i = 0; i < k; ++i) {
    int j = pairing[i];
    ll x = (uu[i] + vv[j]) / 2;
    ll y = (uu[i] - vv[j]) / 2;
    cout << " " << x << " " << y;
  }
  cout << endl;
  cout.flush();
  return 0;
}