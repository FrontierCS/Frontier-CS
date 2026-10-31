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
#include <iostream>
#include <vector>
#include <string>
#include <map>

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

using namespace std;

int movecnt = 0, querycnt = 0;
int f[1100010];

int main(int argc, char *argv[]) {
  /*
   * inf：输入
   * ouf：选手输出
   * ans：标准输出
   */
  registerInteraction(argc, argv);

  int deep = inf.readInt(), seed = inf.readInt();
  memset(f, -1, sizeof(f));
  for(int i = 1; i <= deep; i++){
    int cur = -1;
    while(true){
      seed = (seed*998244353ll+97)%1000000009;
      cur = seed%3;
      if(cur != f[i-1])break;
    }
    f[i] = cur;
  }
  cout.flush();
  cout<<deep<<endl;
  cout.flush();
  while(true){
    string operation = ouf.readWord();
    if(operation == "move"){
      int c = ouf.readInt(0, 2);
      movecnt++;
      if(movecnt > 100000){
        quitf(_wa, "Too many moves");
      }
      if(c == f[deep]){
        deep--;
        if(deep == 0){
          cout<<1<<endl;
          cout.flush();
          double score = calibrated((5001.0 / (querycnt + 1.0)));
    score = natural_log_score(100.0 * score, querycnt, 5000.0L, true) / 100.0;
          double unbounded_ratio = score;
          quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_ratio);
        }
        else{
          cout<<0<<endl;
          cout.flush();
        }
      }
      else{
        deep++;
        f[deep] = c;
        cout<<0<<endl;
        cout.flush();
      }
    }
    else if(operation == "query"){
      querycnt++;
      if(querycnt > 100000){
        quitf(_wa, "Too many queries");
      }
      cout<<deep<<endl;
      cout.flush();
    }
    else{
      quitf(_wa, "Invalid operation");
    }
  }
  quitf(_wa, "Exit not founded");
}
