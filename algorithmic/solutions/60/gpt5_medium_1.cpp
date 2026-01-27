#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 100000;
static const int STEP = 200;
static const int HALF = STEP / 2;

long double read_response() {
    long double resp;
    if (!(cin >> resp)) {
        // If input stream ends unexpectedly, terminate.
        exit(0);
    }
    return resp;
}

long double queryV(int x) {
    cout << "query " << x << " 0 " << x << " " << MAXC << endl;
    cout.flush();
    return read_response();
}

long double queryH(int y) {
    cout << "query 0 " << y << " " << MAXC << " " << y << endl;
    cout.flush();
    return read_response();
}

bool find_two_positive_vertical(int &c1, long double &l1, int &c2, long double &l2) {
    const long double EPS = 1e-9L;
    for (int pass = 0; pass < 2; ++pass) {
        int offset = pass == 0 ? 0 : HALF;
        for (int c = offset; c <= MAXC; c += STEP) {
            long double l = queryV(c);
            if (l > EPS) {
                c1 = c; l1 = l;
                // Try nearby positions to get a second positive
                // First try +/- HALF
                if (c1 + HALF <= MAXC) {
                    long double ltry = queryV(c1 + HALF);
                    if (ltry > EPS) { c2 = c1 + HALF; l2 = ltry; return true; }
                }
                if (c1 - HALF >= 0) {
                    long double ltry = queryV(c1 - HALF);
                    if (ltry > EPS) { c2 = c1 - HALF; l2 = ltry; return true; }
                }
                // Then try +/- STEP
                if (c1 + STEP <= MAXC) {
                    long double ltry = queryV(c1 + STEP);
                    if (ltry > EPS) { c2 = c1 + STEP; l2 = ltry; return true; }
                }
                if (c1 - STEP >= 0) {
                    long double ltry = queryV(c1 - STEP);
                    if (ltry > EPS) { c2 = c1 - STEP; l2 = ltry; return true; }
                }
                // Finally, try small deltas up to HALF-1
                for (int d = 1; d < HALF; ++d) {
                    if (c1 + d <= MAXC) {
                        long double ltry = queryV(c1 + d);
                        if (ltry > EPS) { c2 = c1 + d; l2 = ltry; return true; }
                    }
                    if (c1 - d >= 0) {
                        long double ltry = queryV(c1 - d);
                        if (ltry > EPS) { c2 = c1 - d; l2 = ltry; return true; }
                    }
                }
                // If still not found (very unlikely), continue scanning to find next positive
            }
        }
    }
    return false;
}

bool find_two_positive_horizontal(int &c1, long double &l1, int &c2, long double &l2) {
    const long double EPS = 1e-9L;
    for (int pass = 0; pass < 2; ++pass) {
        int offset = pass == 0 ? 0 : HALF;
        for (int c = offset; c <= MAXC; c += STEP) {
            long double l = queryH(c);
            if (l > EPS) {
                c1 = c; l1 = l;
                // Try nearby positions to get a second positive
                // First try +/- HALF
                if (c1 + HALF <= MAXC) {
                    long double ltry = queryH(c1 + HALF);
                    if (ltry > EPS) { c2 = c1 + HALF; l2 = ltry; return true; }
                }
                if (c1 - HALF >= 0) {
                    long double ltry = queryH(c1 - HALF);
                    if (ltry > EPS) { c2 = c1 - HALF; l2 = ltry; return true; }
                }
                // Then try +/- STEP
                if (c1 + STEP <= MAXC) {
                    long double ltry = queryH(c1 + STEP);
                    if (ltry > EPS) { c2 = c1 + STEP; l2 = ltry; return true; }
                }
                if (c1 - STEP >= 0) {
                    long double ltry = queryH(c1 - STEP);
                    if (ltry > EPS) { c2 = c1 - STEP; l2 = ltry; return true; }
                }
                // Finally, try small deltas up to HALF-1
                for (int d = 1; d < HALF; ++d) {
                    if (c1 + d <= MAXC) {
                        long double ltry = queryH(c1 + d);
                        if (ltry > EPS) { c2 = c1 + d; l2 = ltry; return true; }
                    }
                    if (c1 - d >= 0) {
                        long double ltry = queryH(c1 - d);
                        if (ltry > EPS) { c2 = c1 - d; l2 = ltry; return true; }
                    }
                }
                // If still not found (very unlikely), continue scanning to find next positive
            }
        }
    }
    return false;
}

long long round_ll(long double x) {
    return (long long) llround(x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Find two vertical positives
    int vx1 = -1, vx2 = -1;
    long double vl1 = 0, vl2 = 0;
    bool okv = find_two_positive_vertical(vx1, vl1, vx2, vl2);
    if (!okv) {
        // Fallback: if unable to find, terminate
        return 0;
    }

    // Compute x center from two vertical chords
    long double f1 = 0.25L * vl1 * vl1;
    long double f2 = 0.25L * vl2 * vl2;
    long double denomx = 2.0L * ((long double)vx1 - (long double)vx2);
    long double xc = ( (f1 - f2) + ((long double)vx1 * (long double)vx1 - (long double)vx2 * (long double)vx2) ) / denomx;
    long long xi_ll = round_ll(xc);
    int xi = (int)max(0LL, min((long long)MAXC, xi_ll));

    // Query at x = xi to get 2r
    long double lv = queryV(xi);
    long long r1 = round_ll(lv / 2.0L);

    // Find two horizontal positives
    int hy1 = -1, hy2 = -1;
    long double hl1 = 0, hl2 = 0;
    bool okh = find_two_positive_horizontal(hy1, hl1, hy2, hl2);
    if (!okh) {
        // Fallback: if unable to find, terminate
        return 0;
    }

    // Compute y center from two horizontal chords
    long double g1 = 0.25L * hl1 * hl1;
    long double g2 = 0.25L * hl2 * hl2;
    long double denomy = 2.0L * ((long double)hy1 - (long double)hy2);
    long double yc = ( (g1 - g2) + ((long double)hy1 * (long double)hy1 - (long double)hy2 * (long double)hy2) ) / denomy;
    long long yi_ll = round_ll(yc);
    int yi = (int)max(0LL, min((long long)MAXC, yi_ll));

    // Query at y = yi to get 2r (for confirmation)
    long double lh = queryH(yi);
    long long r2 = round_ll(lh / 2.0L);

    // Choose r (they should match)
    long long r = r1;
    if (llabs(r1 - r2) > 0) {
        // In case of discrepancy, choose the more plausible one by extra check at x=xi (already queried) and y=yi (already queried).
        // Prefer the smaller to ensure inside bounds.
        r = min(r1, r2);
    }

    // Output the answer
    cout << "answer " << xi << " " << yi << " " << r << endl;
    cout.flush();

    return 0;
}