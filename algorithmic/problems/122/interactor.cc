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
#include <string>

using namespace std;

int n = 0, a[100010];

int check(int w){
  int L = 1, S = 0;
  for(int i = 1; i <= n; i++){
    if(a[i] > w)return 0;
    if(S+a[i] <= w)S += a[i];
    else S = a[i], L++;
  }
  return L;
}

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: player output
   * ans: standard output
   */

  registerInteraction(argc, argv);

  int t = 1;
  cout.flush();
  cout<<t<<endl;
  cout.flush();
  int sumn = 0;
  int l = 0, r = 0;
  string op = ouf.readWord();
  if(op == "!"){
    int w = ouf.readInt();
    quitf(_wa, "Wrong guess");
  }
  else if(op == "?"){
    n = ouf.readInt(1, 100000);
    sumn += n;
    int maxa = 0;
    for(int i = 1; i <= n; i++){
      a[i] = ouf.readInt(1, 100000);
      maxa = max(maxa, a[i]);
    }
    if(maxa >= 50000){
      cout<<0<<endl;
      cout.flush();
      l = 1, r = maxa-1;
    }
    else{
      int L1 = check(100000);
      int L2 = check(maxa);
      int L = min(L2, L1+1);
      cout<<L<<endl;
      cout.flush();

      l = maxa-1, r = 100000;
      int ansl = 0, ansr = 0;
      while(l < r){
        int mid = (l+r)/2;
        if(check(mid) <= L){
          ansl = mid;
          r = mid;
        }
        else l = mid+1;
      }

      l = maxa-1, r = 100000;
      while(l < r){
        int mid = (l+r)/2;
        if(check(mid) >= L){
          ansr = mid;
          l = mid+1;
        }
        else r = mid;
      }

      l = ansl, r = ansr;
    }
  }
  else{
    quitf(_wa, "Invalid operation");
  }

  int chosen = l+inf.readInt()%(r-l+1);
  op = ouf.readWord();
  if(op == "!"){
    int w = ouf.readInt();
    if(l == r && l == w){
      double score = (200000.0-1.0*sumn)/(200000.0-23867.0);
      score = reference_score(score);
    score = natural_log_score(100.0 * score, sumn, 23867.0L, true) / 100.0;
      quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, score);
    }
    else quitf(_wa, "Wrong guess");
  }
  else if(op == "?"){
    n = ouf.readInt(1, 100000);
    sumn += n;
    for(int i = 1; i <= n; i++){
      a[i] = ouf.readInt(1, 100000);
    }
    cout<<check(chosen)<<endl;
    cout.flush();
  }
  else{
    quitf(_wa, "Invalid operation");
  }

  op = ouf.readWord();
  if(op == "!"){
    int w = ouf.readInt();
    if(w == chosen){
      double score = (210000.0-1.0*sumn)/(210000.0-23867.0);
      score = reference_score(score);
    score = natural_log_score(100.0 * score, sumn, 23867.0L, true) / 100.0;
      double unbounded_score = score;
      quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
    }
    else quitf(_wa, "Wrong guess");
  }
  else if(op == "?"){
    quitf(_wa, "Too many queries");
  }
  else{
    quitf(_wa, "Invalid operation");
  }
}
