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
#include <bits/stdc++.h>
using namespace std;
static double referenceScore(double r) { return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r); }


const int MAXN = 100005;
int p[MAXN];

static const int N_SUM_LIMIT = 100000;
static const int SEGMENT_SUM_MULT = 30;

int secondLargestPos(int /*n*/, int l, int r) {
    int mxVal = -1, mxPos = -1;
    int seVal = -1, sePos = -1;
    for (int i = l; i <= r; i++) {
        int v = p[i];
        if (v > mxVal) {
            seVal = mxVal; sePos = mxPos;
            mxVal = v;     mxPos = i;
        } else if (v > seVal) {
            seVal = v;     sePos = i;
        }
    }
    return sePos;
}

double perCaseScoreBounded(int q, int n) {
    double L = log2((double)n);
    if (q >= 15.0 * L) return 0.0;
    return natural_log_score(100.0 * referenceScore((15.0 * L - (double)q) / (14.0 * L)), q, L, true);
}

double perCaseRatioUnbounded(int q, int n) {
    double L = log2((double)n);
    if (q >= 15.0 * L) return 0.0;
    return natural_log_score(100.0 * referenceScore((15.0 * L - (double)q) / (14.0 * L)), q, L, true);
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int T = inf.readInt();
    int nsum = 0;
    cout << T << endl;

    double minScoreBoundedPct = 100.0;
    double minRatioUnbounded  = 0.0;
    bool firstCase = true;

    int totalQueries = 0;

    for (int tc = 0; tc < T; tc++) {
        int n = inf.readInt();
        nsum += n;
        for (int i = 1; i <= n; i++) {
            p[i] = inf.readInt();
        }

        cout << n << endl;

        int posN = -1;
        for (int i = 1; i <= n; i++) {
            if (p[i] == n) {
                posN = i;
                break;
            }
        }
        if (posN == -1) quitf(_fail, "value n not found (test %d)", tc + 1);

        int segSum = 0, queries = 0;
        int segLimit = SEGMENT_SUM_MULT * n;

        while (true) {
            string op = ouf.readToken();
            if (op == "?") {
                int l = ouf.readInt(1, n, "l");
                int r = ouf.readInt(1, n, "r");
                if (!(l < r)) quitf(_pe, "expected l<r; got l=%d r=%d", l, r);
                int len = r - l + 1;
                if (segSum + len > segLimit) {
                    quitf(_wa, "sum of (r-l+1) exceeds %d (attempt %d) on test %d",
                          segLimit, segSum + len, tc + 1);
                }
                segSum += len;
                queries++;

                int pos = secondLargestPos(n, l, r);
                cout << pos << endl;
            } else if (op == "!") {
                int x = ouf.readInt(1, n, "x");
                if (x != posN) {
                    quitf(_wa, "wrong position on test %d: expected %d, got %d",
                          tc + 1, posN, x);
                }

                double boundedPct = perCaseScoreBounded(queries, n);
                double unboundedRatio = perCaseRatioUnbounded(queries, n);

                if (firstCase) {
                    minScoreBoundedPct = boundedPct;
                    minRatioUnbounded  = unboundedRatio;
                    firstCase = false;
                } else {
                    minScoreBoundedPct = min(minScoreBoundedPct, boundedPct);
                    minRatioUnbounded  = min(minRatioUnbounded,  unboundedRatio);
                }

                totalQueries += queries;
                break;
            } else {
                quitf(_pe, "unknown command '%s' on test %d", op.c_str(), tc + 1);
            }
        }
    }

    double score_ratio = minScoreBoundedPct / 100.0;
    double unbounded_ratio = minRatioUnbounded / 100.0;

    quitp(score_ratio,
          "all %d tests passed; Ratio: %.12f; RatioUnbounded: %.12f; total queries = %d",
          T, score_ratio, unbounded_ratio, totalQueries);
    return 0;
}
