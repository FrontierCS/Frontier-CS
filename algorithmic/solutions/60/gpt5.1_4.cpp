#include <bits/stdc++.h>
using namespace std;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << endl;
    cout.flush();
    double res;
    if (!(cin >> res)) {
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAXC = 100000;
    const int STEP = 199;
    const double EPS_POS = 1e-3;

    // 1. Find one vertical line that intersects the circle.
    int x0 = -1;
    for (int x = 0; x <= MAXC; x += STEP) {
        double len = ask(x, 0, x, MAXC);
        if (len > EPS_POS) {
            x0 = x;
            break;
        }
    }

    if (x0 == -1) {
        // Should not happen for valid tests.
        x0 = MAXC / 2;
    }

    // 2. Binary search for leftmost and rightmost x with positive intersection.
    int lo, hi;

    // Left boundary: smallest x in [0, x0] with positive length.
    lo = 0;
    hi = x0;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = ask(mid, 0, mid, MAXC);
        if (len > EPS_POS) hi = mid;
        else lo = mid;
    }
    int Lx = hi;

    // Right boundary: largest x in [x0, MAXC] with positive length.
    lo = x0;
    hi = MAXC;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = ask(mid, 0, mid, MAXC);
        if (len > EPS_POS) lo = mid;
        else hi = mid;
    }
    int Rx = lo;

    int cx = (Lx + Rx) / 2;
    int r  = (Rx - Lx + 2) / 2;

    // 3. Find cy using vertical segments from y=0 to y=Y at x = cx.
    //    Let L(Y) be intersection length on segment [0, Y]. For integers:
    //    L(Y) < r  iff Y < cy
    //    L(Y) >= r iff Y >= cy
    //    (since along x=cx, circle spans [cy-r, cy+r] and r >= 100)
    double target = r - 0.5;  // Safe threshold between r-1 and r considering errors.

    lo = 0;
    hi = MAXC;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = ask(cx, 0, cx, mid);
        if (len >= target) hi = mid;
        else lo = mid;
    }
    int cy = hi;

    cout << "answer " << cx << ' ' << cy << ' ' << r << endl;
    cout.flush();
    return 0;
}