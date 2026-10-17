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

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <iostream>
#include <map>

using namespace std;

int C[300][300];
int dx[4] = {1, 0, -1, 0}, dy[4] = {0, 1, 0, -1};

map<pair<int, int>, bool>g, vis;

int main(int argc, char *argv[]) {
  /*
   * inf: input file
   * ouf: contestant output
   * ans: standard output
   */
  registerTestlibCmd(argc, argv);

  int t = inf.readInt(1, 1);
  int n = inf.readInt(), m = inf.readInt();
  for(int i = 1; i <= m; i++){
    int a = inf.readInt(), b = inf.readInt();
    g[make_pair(a, b)] = true;
    g[make_pair(b, a)] = true;
  }

  int P = ouf.readInt(1, 240);
  for(int i = 1; i <= P; i++){
    int Q = ouf.readInt(P, P);
  }
  for(int i = 1; i <= P; i++){
    for(int j = 1; j <= P; j++){
      C[i][j] = ouf.readInt(1, n);
    }
  }

  for(int i = 1; i <= P; i++){
    for(int j = 1; j <= P; j++){
      for(int k = 0; k < 4; k++){
        int toi = i+dx[k];
        int toj = j+dy[k];
        if(toi < 1 || toi > P || toj < 1 || toj > P)continue;
        if(C[i][j] != C[toi][toj] && !g[make_pair(C[i][j], C[toi][toj])])quitf(_wa, "Edge not exist");
        vis[make_pair(C[i][j], C[toi][toj])] = true;
        vis[make_pair(C[toi][toj], C[i][j])] = true;
      }
    }
  }

  for(int i = 1; i <= n; i++){
    for(int j = 1; j <= n; j++){
      if(g[make_pair(i, j)] && !vis[make_pair(i, j)])quitf(_wa, "Edge not represented");
    }
  }
  double R = (1.0*P)/(1.0*n);
  double score = (6-R)/(6-1.5);
  score = max(score, 0.0);
  score = referenceScore(score);
    score = natural_log_score(100.0 * score, P, 1.5L*n, true) / 100.0;
  double unbounded_score = score;
  quitp(score, "Ratio: %.12lf, RatioUnbounded: %.12lf", score, unbounded_score);
}
