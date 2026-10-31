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
// Performance anchor: 60 points; logarithmic credit above it.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <iostream>
#include <vector>

using namespace std;

vector<int>v[5010];
int fa[5010], depth[5010];
int X[5010], Y[5010];

void dfs(int x, int f){
  fa[x] = f;
  for(int i = 0; i < v[x].size(); i++){
    int y = v[x][i];
    if(y==f)continue;
    depth[y] = depth[x]+1;
    dfs(y, x);
  }
}

int main(int argc, char *argv[]) {
  /*
   * inf: input
   * ouf: contestant output
   * ans: standard output
   */
  registerInteraction(argc, argv);

  int t = inf.readInt(1, 1), n = inf.readInt(5000, 5000);
  for(int i = 1; i < n; i++){
    int x = inf.readInt(1, n), y = inf.readInt(1, n);
    X[i] = x, Y[i] = y;
    v[x].push_back(y);
    v[y].push_back(x);
  }
  depth[1] = 0;
  dfs(1, 1);
  int target = inf.readInt(1, n);
  cout<<t<<endl;
  cout.flush();
  cout<<n<<endl;
  cout.flush();
  for(int i = 1; i < n; i++){
    cout<<X[i]<<" "<<Y[i]<<endl;
    cout.flush();
  }
  int sum_depth = 0;
  for(int i = 1; i <= 500; i++){
    char s = ouf.readChar();
    if(s == '?'){
      ouf.readSpace();
      int x = ouf.readInt(1, n);
      sum_depth += depth[x];
      ouf.readEoln();
      int y = target;
      while(y != 1 && y != x){
        y = fa[y];
      }
      if(y != x){
        cout<<0<<endl;
        cout.flush();
        target = fa[target];
      }
      else{
        cout<<1<<endl;
        cout.flush();
      }
    }
    else if(s == '!'){
      ouf.readSpace();
      int guess = ouf.readInt(1, n);
      ouf.readEoln();
      ouf.readEof();
      if(guess == target){
        int best = ans.readInt();
        double score = (3.0*best-1.0*sum_depth)/(2.0*best); // Get full score if less than 1.5*best, get half if less than 2.0*best
        score = reference_score(score);
    score = natural_log_score(100.0 * score, sum_depth, best, true) / 100.0;
        double unbounded_score = score;
        quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
      }
      else{
        quitf(_wa, "Wrong node, expected %d, output %d", target, guess);
      }
    }
    else{
      quitf(_wa, "Invalid operation");
    }
  }

  quitf(_wa, "Too many queries");
}
