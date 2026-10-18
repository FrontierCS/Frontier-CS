#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"
#include <iostream>
#include <vector>

using namespace std;
static double referenceScore(double r) { return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r); }


int cost[5010];

vector<int>v[5010];

int vis[1010];

int main(int argc, char *argv[]) {
  /*
   * inf：输入
   * ouf：选手输出
   * ans：标准输出
   */
  registerTestlibCmd(argc, argv);

  int n = inf.readInt(1, 400), m = inf.readInt(1, 4000);
  for(int i = 1; i <= m; i++){
    cost[i] = inf.readInt();
  }
  for(int i = 1; i <= n; i++){
    int k = inf.readInt(1, m);
    for(int j = 1; j <= k; j++){
      int sid = inf.readInt(1, m);
      v[sid].push_back(i);
    }
  }

  int cnt = ouf.readInt(1, m);
  long long totcost = 0;
  for(int i = 1; i <= cnt; i++){
    int sid = ouf.readInt(1, m);
    totcost += cost[sid];
    for(int j = 0; j < v[sid].size(); j++){
      vis[v[sid][j]] = 1;
    }
  }

  for(int i = 1; i <= n; i++){
    if(!vis[i])quitf(_wa, "Invalid answer");
  }

  // quitf(_ok, "cost is %d", totcost);

  int ref = ans.readInt();
  if (ref <= 0) quitf(_fail, "Reference cost must be positive");
  double score = (2.0*ref-1.0*totcost)/(1.0*ref);
  score = max(score, 0.0);
  score = referenceScore(score);
    score = natural_log_score(100.0 * score, totcost, ref, true) / 100.0;
  double unbounded_score = score;
  quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
}
