#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}


#include <algorithm>
// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
 
#define rep(i, a, b) for(int i = a; i < (b); ++i)
#define trav(a, x) for(auto& a : x)
#define all(x) x.begin(), x.end()
#define sz(x) (int)(x).size()
typedef long long ll;
typedef pair<int, int> pii;
typedef vector<int> vi;
typedef vector<vi> vvi;

int main(int argc, char *argv[]) {
  /*
   * inf: input file
   * ouf: contestant output
   * ans: standard output
   */
  registerTestlibCmd(argc, argv);


	int n = inf.readInt(), q = inf.readInt();
	vector<int> a(n + 1);
	for(int i = 1; i <= n; i++){
		a[i] = inf.readInt();
	}
	vector<pair<int, int>> requirements(q);
	for(int i = 0; i < q; i++){
		int l = inf.readInt();
		int r = inf.readInt();
		requirements[i] = make_pair(l, r);
	}

  int cnt_e = ouf.readInt(n, 2200000);
  vector<int> size(cnt_e + 1), mn(cnt_e + 1), mx(cnt_e + 1);
  vector<int> l(cnt_e + 1), r(cnt_e + 1);
  rep(i, 1, n + 1) {
    mn[i] = a[i];
    mx[i] = a[i];
    l[i] = -1;
    r[i] = -1;
    size[i] = 1;
  }
  int cnt = n;
  rep(i, n + 1, cnt_e + 1) {
    int u = ouf.readInt(1, cnt), v = ouf.readInt(1, cnt);
    if (mx[u] < mn[v] || mn[u] > mx[v]) {
      l[i] = u;
      r[i] = v;
      size[i] = size[u] + size[v];
      mn[i] = min(mn[u], mn[v]);
      mx[i] = max(mx[u], mx[v]);
      cnt++;
    } else {
			quitf(_wa, "Invalid operation %d: g(%d) = %d, f(%d) = %d, g(%d) = %d, f(%d) = %d", i, u, mx[u], u, mn[u], v, mx[v], v, mn[v]);
		}
  }

	vector<int> vis;

	for (int i = 1; i <= q; i++) {
		int k = ouf.readInt(1, cnt);
		queue<int> q;
		q.push(k);
	
		vis.clear();
		vis.resize(requirements[i - 1].second - requirements[i - 1].first + 1);
		while (!q.empty()) {
			int u = q.front();
			q.pop();
			if (l[u] != -1) {
				q.push(l[u]);
				q.push(r[u]);
			} else {
				int idx = u - requirements[i - 1].first;
				if (idx < 0 || idx >= sz(vis)) {
					quitf(_wa, "Invalid set %d", i);
				}
				if (vis[idx]) {
					quitf(_wa, "Invalid set %d", i);
				}
				vis[idx] = 1;
			}
		}
	}
	
	double score = (double)(2.2 * 1000000 - cnt_e) / (2.2 * 1000000);

  score = bounded_base_ratio(score);
  score = natural_log_score(100.0L * (score), cnt_e, 880000.0L, true) / 100.0;
  quitp(score, "Ratio: %.12f, RatioUnbounded: %.12f", score, score);
}
