#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}

#include "testlib.h"
// Performance anchor: 60 points; logarithmic credit above it.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <iostream>
#include <vector>
#include <set>

using namespace std;

set<int>s[5];

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: player output
   * ans: standard output
   */
  registerTestlibCmd(argc, argv);

  int n = inf.readInt();
  for(int i = 1; i <= n; i++){
    s[1].insert(i);
  }
  int m = ouf.readInt();
  for(int i = 1; i <= m; i++){
    int a = ouf.readInt(1, 3), b = ouf.readInt(1, 3);
    if(a == b)quitf(_wa, "Same basket");
    if(s[a].empty())quitf(_wa, "Empty basket a");
    int mida = (s[a].size()+2)/2;
    set<int>::iterator it;
    for(it = s[a].begin(); it != s[a].end(); it++){
      mida--;
      if(mida == 0)break;
    }
    int val = (*it);
    s[a].erase(val);
    s[b].insert(val);
    int midb = (s[b].size()+2)/2;
    for(it = s[b].begin(); it != s[b].end(); it++){
      midb--;
      if(midb == 0)break;
    }
    if((*it) != val)quitf(_wa, "Invalid target basket b on %d operation", i);
  }
  if(s[3].size()==n){
    int ref = ans.readInt();
    double score = (2.0*ref-1.0*m)/(1.0*ref);
    if (score < 0) score = 0.0;
    score = reference_score(score);
    score = natural_log_score(100.0 * score, m, ref, true) / 100.0;
    double unbounded_score = score;
    quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
  }
  else quitf(_wa, "Invalid operation");
}
