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


// Legacy base ratio, retained only to decide and preserve the lower band.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
  registerTestlibCmd(argc, argv);

  int n = inf.readInt(1, 1000);
  int m = inf.readInt(0, 1000000);

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
  ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, bad, 0.4L*m, true) / 100.0;
  quitp(ratio, "Ratio: %.12f", ratio);
}
