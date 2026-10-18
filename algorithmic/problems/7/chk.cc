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

// Continuous reference calibration; the performance anchor earns 60 points.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <iostream>
#include <vector>

using namespace std;

vector<pair<int, int> >v[150];
int l, r;
int in[150], out[150];
int cnt = 0;
int vis[1000010];

void dfs(int x, int val){
  if(out[x] == 0){
    cnt++;
    if(cnt > 1e6)quitf(_wa, "too many roads");
    if(val < l || val > r) quitf(_wa, "number outside interval");
    vis[val]++;
    if(vis[val] > 1)quitf(_wa, "repeated roads");
    return;
  }
  for(int i = 0; i < out[x]; i++){
    dfs(v[x][i].first, val*2+v[x][i].second);
  }
}

int main(int argc, char *argv[]) {
  /*
   * inf：输入
   * ouf：选手输出
   * ans：标准输出
   */
  registerTestlibCmd(argc, argv);

  l = inf.readInt(), r = inf.readInt();

  int n = ouf.readInt(1, 100);
  for(int i = 1; i <= n; i++){
    out[i] = ouf.readInt(0, 200);
    for(int j = 1; j <= out[i]; j++){
      int a = ouf.readInt(1, n), val = ouf.readInt(0, 1);
      if(a == i)quitf(_wa, "self-loop");
      v[i].push_back(make_pair(a, val));
      in[a]++;
    }
  }

  // 1 in 0 and 1 out 0, no leading 0
  int cnt1 = 0, cnt2 = 0;
  for(int i = 1; i <= n; i++){
    if(in[i] == 0)cnt1++;
    if(out[i] == 0)cnt2++;
    if(in[i] == 0){
      for(int j = 0; j < out[i]; j++){
        if(v[i][j].second == 0)quitf(_wa, "leading 0");
      }
    }
  }
  if(cnt1 != 1 || cnt2 != 1)quitf(_wa, "more than one indegree or outdegree 0");

  for(int i = 1; i <= n; i++){
    if(in[i] == 0)dfs(i, 0);
  }
  for(int i = l; i <= r; i++){
    if(vis[i] == 0)quitf(_wa, "number not represented");
  }

  double score = (100.0-1.0*n)/(100.0-50.0);
  score = max(score, 0.0);
  double unbounded_score = score;
  score = referenceScore(score);
    score = natural_log_score(100.0 * score, n, 50, true) / 100.0;
  unbounded_score = score;
  quitp(score, "Ratio: %.12f, RatioUnbounded: %.12f", score, unbounded_score);
}
