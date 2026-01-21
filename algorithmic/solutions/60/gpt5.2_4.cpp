#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 100000;

struct Interactor {
    int qcnt = 0;

    double ask(int x1, int y1, int x2, int y2) {
        cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << "\n" << flush;
        double res;
        if (!(cin >> res)) exit(0);
        qcnt++;
        return res;
    }

    void answer(int x, int y, int r) {
        cout << "answer " << x << ' ' << y << ' ' << r << "\n" << flush;
        exit(0);
    }
};

static inline bool isnan_d(double v) { return std::isnan(v); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;

    const double EPS_POS = 1e-4;
    const double EPS_FULL = 1e-3;

    vector<double> vfull(MAXC + 1, numeric_limits<double>::quiet_NaN());

    auto verticalFull = [&](int x) -> double {
        if (!isnan_d(vfull[x])) return vfull[x];
        vfull[x] = it.ask(x, 0, x, MAXC);
        return vfull[x];
    };

    auto isPosFull = [&](int x) -> bool {
        return verticalFull(x) > EPS_POS;
    };

    int x_in = -1;
    const int STEP = 199;
    for (int x = 0; x <= MAXC; x += STEP) {
        if (isPosFull(x)) {
            x_in = x;
            break;
        }
    }
    if (x_in == -1) {
        // Fallback scan (should never be needed)
        for (int x = 0; x <= MAXC; x++) {
            if (isPosFull(x)) { x_in = x; break; }
        }
    }
    if (x_in == -1) return 0;

    // Find first x with positive intersection (left_pos)
    int lo = 0, hi = x_in;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        if (isPosFull(mid)) hi = mid;
        else lo = mid + 1;
    }
    int left_pos = lo;

    // Find last x with positive intersection (right_pos)
    lo = x_in; hi = MAXC;
    while (lo < hi) {
        int mid = (lo + hi + 1) >> 1;
        if (isPosFull(mid)) lo = mid;
        else hi = mid - 1;
    }
    int right_pos = lo;

    int x_left_tan = left_pos - 1;
    int x_right_tan = right_pos + 1;
    int x0 = (x_left_tan + x_right_tan) / 2;
    int r = (x_right_tan - x_left_tan) / 2;

    // Now find y interval using prefix segments on x = x0
    vector<double> vprefix(MAXC + 1, numeric_limits<double>::quiet_NaN());
    auto verticalPrefix = [&](int Y) -> double {
        if (!isnan_d(vprefix[Y])) return vprefix[Y];
        vprefix[Y] = it.ask(x0, 0, x0, Y);
        return vprefix[Y];
    };

    auto isPosPrefix = [&](int Y) -> bool {
        return verticalPrefix(Y) > EPS_POS;
    };
    auto isFullPrefix = [&](int Y) -> bool {
        return verticalPrefix(Y) >= 2.0 * r - EPS_FULL;
    };

    // y_low: tangent at bottom = first positive Y - 1
    lo = 1; hi = MAXC;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        if (isPosPrefix(mid)) hi = mid;
        else lo = mid + 1;
    }
    int y_low = lo - 1;

    // y_high: first Y where prefix reaches full 2r
    lo = 1; hi = MAXC;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        if (isFullPrefix(mid)) hi = mid;
        else lo = mid + 1;
    }
    int y_high = lo;

    int y0 = (y_low + y_high) / 2;
    // Optional consistency check; if mismatch, trust x-derived r.
    // int r2 = (y_high - y_low) / 2;

    it.answer(x0, y0, r);
    return 0;
}