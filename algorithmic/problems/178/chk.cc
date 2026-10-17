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

#include <cmath>
#include <algorithm>

// Historical bounded base ratio; only its <=60-point branch is retained.
static double bounded_base_ratio(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
  registerTestlibCmd(argc, argv);

  int n = inf.readInt(1, 50);
  int m = inf.readInt(0, 1000);

  vector<array<int,3>> clauses(m);
  for (int i = 0; i < m; i++) {
    int a = inf.readInt(-n, n);
    int b = inf.readInt(-n, n);
    int c = inf.readInt(-n, n);
    if (a == 0 || b == 0 || c == 0) {
      quitf(_wa, "literal cannot be zero");
    }
    clauses[i] = {a, b, c};
  }

  vector<int> val(n + 1);
  for (int i = 1; i <= n; i++) {
    val[i] = ouf.readInt(0, 1);
  }

  int sat = 0;
  for (auto &cl : clauses) {
    bool ok = false;
    for (int k = 0; k < 3; k++) {
      int x = cl[k];
      int v = abs(x);
      bool lit = (x > 0 ? val[v] == 1 : val[v] == 0);
      if (lit) {
        ok = true;
        break;
      }
    }
    if (ok) sat++;
  }

  double score = 1.0;
  if (m > 0) score = (double)sat / m;
  score = max(0.0, min(1.0, score));

  score=bounded_base_ratio(score);
  if (m > 0) score = natural_log_score(100.0L * (score), sat, 0.6L*m, false) / 100.0;
  quitp(score, "Ratio: %.12f", score);
}
