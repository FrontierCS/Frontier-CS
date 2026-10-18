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
#include <iostream>
#include <map>
#include <algorithm>

using namespace std;
typedef long long ll;
int C[300][300];
int dx[4] = {1, 0, -1, 0}, dy[4] = {0, 1, 0, -1};



int main(int argc, char *argv[]) {
  /*
   * inf: input file
   * ouf: contestant output
   * ans: standard output
   */
  registerTestlibCmd(argc, argv);

  int n = inf.readInt(), x = inf.readInt();
  vector<long long> inp(n);
  for(int i = 0; i < n; i++){
    inp[i] = inf.readInt(1, (ll)1e9);
  }

  int res = ouf.readInt();
  for(int i = 0; i < 10; i++){
    int l = ouf.readInt(1, n);
    int r = ouf.readInt(l, n);
    int d = ouf.readInt();
    l--, r--;
    for(int j = l; j <= r; j++){
      inp[j] += d;
    }
  }
  auto calc_lis = [&](vector<ll> v){
    const ll INF = (ll)1e18;
    vector<ll> dp(v.size() + 1, INF);
    for(int i = 0; i < v.size(); i++){
      int pos = lower_bound(dp.begin(), dp.end(), v[i]) - dp.begin();
      dp[pos] = v[i];
    }
    return lower_bound(dp.begin(), dp.end(), INF) - dp.begin();
  };

  int real_lis = calc_lis(inp);
  
  if (real_lis != res) quitf(_wa, "wrong answer");

  double score_ratio = (double)res / (double)n;
  score_ratio = bounded_base_ratio(score_ratio);
  score_ratio = natural_log_score(100.0L * (score_ratio), res, 0.6L*n, false) / 100.0;
  quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f", res, score_ratio, score_ratio);

}