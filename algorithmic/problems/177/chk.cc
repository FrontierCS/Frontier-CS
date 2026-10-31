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

  int n = inf.readInt(1, 60000);
  int m = inf.readInt(0, 200000);

  vector<pair<int,int>> edges(m);
  for (int i = 0; i < m; i++) {
    int u = inf.readInt(1, n);
    int v = inf.readInt(1, n);
    if (u == v) {
      quitf(_wa, "self-loop on node %d", u);
    }
    edges[i] = {u - 1, v - 1};
  }

  vector<int> col(n);
  for (int i = 0; i < n; i++) {
    col[i] = ouf.readInt(1, 3);
  }

  int bad = 0;
  for (auto &[u, v] : edges) {
    if (col[u] == col[v]) bad++;
  }

  double ratio;
  if (m == 0) {
    ratio = 1.0;
  } else {
    ratio = (double)(m - bad) / (double)m;
  }

  ratio = max(0.0, min(1.0, ratio));
  ratio=bounded_base_ratio(ratio);
  ratio = natural_log_score(100.0L * (ratio), bad, 0.4L*m, true) / 100.0;
  quitp(ratio, "Ratio: %.12f", ratio);
}