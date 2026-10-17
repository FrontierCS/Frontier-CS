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
#include <string>
#include <map>

using namespace std;

int WrongPred[1010];

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: contestant output
   * ans: standard output
   */
  registerInteraction(argc, argv);

  int n = inf.readInt(1, 1000), m = inf.readInt(1, 10000);
  cout.flush();
  cout<<n<<" "<<m<<endl;
  cout.flush();
  int wrongpred = 0;
  for(int i = 1; i <= m; i++){
    string pred = inf.readWord();
    int answer = inf.readInt(0, 1);
    for(int j = 0; j < n; j++){
      if(pred[j]-'0' != answer)WrongPred[j]++;
    }
    cout<<pred<<endl;
    cout.flush();
    int outpred = ouf.readInt(0, 1);
    if(outpred != answer)wrongpred++;
    cout<<answer<<endl;
    cout.flush();
  }
  int minwrongpred = m+1;
  for(int i = 0; i < n; i++){
    minwrongpred = min(minwrongpred, WrongPred[i]);
  }
  double score;
  if (minwrongpred == 0) {
    // Zero mistakes is an exact theoretical target, not a performance anchor.
    score = wrongpred == 0 ? 1.0 : 0.0;
  } else {
    double r = max(0.0, (2.0 * minwrongpred - wrongpred) / minwrongpred);
    score = r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * log(r));
    score = natural_log_score(100.0 * score, wrongpred, minwrongpred, true) / 100.0;
  }
  double unbounded_score = score;
  quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
}
