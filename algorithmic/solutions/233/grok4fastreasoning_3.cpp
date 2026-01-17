#include <bits/stdc++.h>
using namespace std;
using ll = long long;
const ll INF = 1LL << 60;
const int MAXN = 505;
ll G[MAXN][MAXN];
bool possible[MAXN][MAXN];
ll dp[MAXN][MAXN];
ll min_prefix_max[1005];
ll min_head_G[1005];
ll pmr[MAXN];
ll max_from2[MAXN];

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n, m;
    cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
      for (int j = 1; j <= n; ++j) {
        cin >> G[i][j];
      }
    }
    // Compute possible
    memset(possible, 0, sizeof(possible));
    possible[1][1] = true;
    for (int x = 1; x <= n; ++x) {
      for (int y = 1; y <= n; ++y) {
        if (x == 1 && y == 1) continue;
        bool from_up = (x > 1) && possible[x - 1][y];
        bool from_left = (y > 1) && possible[x][y - 1] && !(x == 1 && y == 2);
        possible[x][y] = from_up || from_left;
      }
    }
    // Compute dp for min_prefix_max
    for (int i = 1; i <= n; ++i) {
      for (int j = 1; j <= n; ++j) {
        dp[i][j] = INF;
      }
    }
    dp[1][1] = G[1][1];
    for (int x = 1; x <= n; ++x) {
      for (int y = 1; y <= n; ++y) {
        if (x == 1 && y == 1) continue;
        ll cand1 = INF;
        if (x > 1) cand1 = max(dp[x - 1][y], G[x][y]);
        ll cand2 = INF;
        bool allow = (y > 1) && !(x == 1 && y == 2);
        if (allow) cand2 = max(dp[x][y - 1], G[x][y]);
        dp[x][y] = min(cand1, cand2);
      }
    }
    // min_prefix_max
    for (int i = 0; i <= 2 * n - 1; ++i) min_prefix_max[i] = INF;
    for (int x = 1; x <= n; ++x) {
      for (int y = 1; y <= n; ++y) {
        if (dp[x][y] >= INF) continue;
        int k = x + y - 2;
        if (k >= 0 && k <= 2 * n - 2) {
          min_prefix_max[k] = min(min_prefix_max[k], dp[x][y]);
        }
      }
    }
    // min_head_G
    for (int i = 0; i <= 2 * n - 1; ++i) min_head_G[i] = INF;
    for (int x = 1; x <= n; ++x) {
      for (int y = 1; y <= n; ++y) {
        if (possible[x][y]) {
          int k = x + y - 2;
          if (k >= 0 && k <= 2 * n - 2) {
            min_head_G[k] = min(min_head_G[k], G[x][y]);
          }
        }
      }
    }
    // prefix_max_row
    pmr[0] = LLONG_MIN / 2;
    for (int i = 1; i <= n; ++i) {
      pmr[i] = max(pmr[i - 1], G[1][i]);
    }
    // max_from2
    max_from2[1] = 0;
    ll cur = LLONG_MIN / 2;
    for (int j = 2; j <= n; ++j) {
      cur = max(cur, G[1][j]);
      max_from2[j] = cur;
    }
    // collected initial T=1 and T=2
    multiset<ll> collected;
    for (int l = 1; l <= n; ++l) {
      ll val1 = pmr[l];
      collected.insert(val1);
      ll val2;
      if (l == 1) {
        val2 = G[2][1];
      } else {
        ll max_old = pmr[l - 1];
        val2 = max(G[2][1], max_old);
      }
      collected.insert(val2);
    }
    // pq
    using tup = tuple<ll, double, int, int>; // lb, cost, l, T
    priority_queue<tup, vector<tup>, greater<tup>> pq;
    int maxt = 2 * n - 1;
    for (int l = 1; l <= n; ++l) {
      for (int tt = 3; tt <= maxt; ++tt) {
        int kk = tt - 1;
        ll lb;
        if (kk < l) {
          int endf = l - kk;
          ll mfix = (endf < 2 ? 0LL : max_from2[endf]);
          ll mpp = min_prefix_max[kk];
          lb = max(mfix, mpp);
        } else {
          lb = min_head_G[kk];
        }
        double cst = 0.05 + 1.0 / l;
        pq.push({lb, cst, l, tt});
      }
    }
    // query loop
    int queried_cnt = 0;
    int query_limit = 120 * n + m;
    while (true) {
      ll threshold = -1;
      if (collected.size() >= (size_t)m) {
        auto it = collected.begin();
        advance(it, m - 1);
        threshold = *it;
        if (pq.empty() || get<0>(pq.top()) > threshold) {
          break;
        }
      }
      if (pq.empty()) break;
      auto [lbv, cstv, cl, ct] = pq.top();
      pq.pop();
      if (queried_cnt >= query_limit) break; // safety
      cout << "? " << cl << " " << ct << endl;
      cout.flush();
      ll val;
      cin >> val;
      collected.insert(val);
      ++queried_cnt;
    }
    // output
    vector<ll> res;
    auto it = collected.begin();
    for (int i = 0; i < m; ++i, ++it) {
      res.push_back(*it);
    }
    cout << "!";
    for (auto v : res) {
      cout << " " << v;
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}