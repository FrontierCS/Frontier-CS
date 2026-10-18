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

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

using namespace std;

int bits(long long val){
  for(int i = 60; i >= 0; i--){
    if((val>>i)&1ll)return i+1;
  }
  return 0;
}

int modPow(long long a, long long d, long long n){
  __int128 r = 1;
  __int128 x = a;
  int ret = 0;
  for(int i = 0; i < 60; i++){
    int bx = bits(x)+1;
    if(d&(1ll<<i)){
      ret += (bits(r)+1)*bx;
      r = r*x%n;
    }
    ret += bx*bx;
    x = x*x%n;
  }
  return ret;
}

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: contestant output
   * ans: standard output
   */
  registerInteraction(argc, argv);

  long long n = inf.readLong(), d = inf.readLong();
  cout.flush();
  cout<<n<<endl;
  cout.flush();
  for(int i = 1; i <= 30001; i++){
    string operation = ouf.readWord();
    if(operation[0] == '?'){
      long long a = ouf.readLong(0, n-1);
      cout<<modPow(a, d, n)<<endl;
      cout.flush();
    }
    else if(operation[0] == '!'){
      long long answer = ouf.readLong();
      if(answer == d){
        double score = calibrated((30000.0-(i-1.0))/26000.0);
    score = natural_log_score(100.0 * score, i-1, 4000, true) / 100.0;
        double unbounded_ratio = score;
        quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_ratio);
      }
      else{
        quitf(_wa, "Incorrect d");
      }
    }
    else{
      quitf(_wa, "Invalid operation");
    }
  }
  quitf(_wa, "Too many queries");
}
