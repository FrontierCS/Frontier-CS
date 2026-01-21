#include <bits/stdc++.h>
using namespace std;

static const int LIM = 100000;
static const double EPS_IN = 1e-4;
static const double EPS_FULL = 1e-4;

struct Interactor {
    int qcnt = 0;

    double ask(int x1, int y1, int x2, int y2) {
        cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
        cout.flush();
        double res;
        if (!(cin >> res)) exit(0);
        if (res < -0.5) exit(0);
        ++qcnt;
        return res;
    }

    void answer(int x, int y, int r) {
        cout << "answer " << x << " " << y << " " << r << "\n";
        cout.flush();
        exit(0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;

    auto insideX = [&](int x) -> bool {
        double len = it.ask(x, 0, x, LIM);
        return len > EPS_IN;
    };

    int xHit = -1;
    {
        vector<int> probes = {50000, 25000, 75000, 12500, 87500, 37500, 62500};
        for (int x : probes) {
            if (insideX(x)) {
                xHit = x;
                break;
            }
        }
        if (xHit == -1) {
            for (int x = 0; x <= LIM; x += 199) {
                if (insideX(x)) {
                    xHit = x;
                    break;
                }
            }
        }
        if (xHit == -1) exit(0);
    }

    int firstInside = -1, lastInside = -1;

    // Find first inside x in [0, xHit]
    {
        int lo = 0, hi = xHit;
        // Ensure hi is inside; otherwise fallback to scanning inward (shouldn't happen)
        if (!insideX(hi)) {
            for (int x = xHit; x >= 0; --x) {
                if (insideX(x)) { hi = x; break; }
            }
        }
        while (lo + 1 < hi) {
            int mid = (lo + hi) / 2;
            if (insideX(mid)) hi = mid;
            else lo = mid;
        }
        firstInside = hi;
    }

    // Find last inside x in [xHit, LIM]
    {
        int lo = xHit, hi = LIM;
        if (!insideX(lo)) {
            for (int x = xHit; x <= LIM; ++x) {
                if (insideX(x)) { lo = x; break; }
            }
        }
        while (lo + 1 < hi) {
            int mid = (lo + hi) / 2;
            if (insideX(mid)) lo = mid;
            else hi = mid;
        }
        lastInside = lo;
    }

    int leftB = firstInside - 1;
    int rightB = lastInside + 1;
    int cx = (leftB + rightB) / 2;
    int r = (rightB - leftB) / 2;

    auto prefixLenY = [&](int t) -> double {
        if (t <= 0) return 0.0;
        if (t > LIM) t = LIM;
        return it.ask(cx, 0, cx, t);
    };

    int tStart = -1, tFull = -1;

    // Find first t such that prefixLenY(t) > 0
    {
        int lo = 0, hi = LIM; // hi must be true
        while (lo + 1 < hi) {
            int mid = (lo + hi) / 2;
            double len = prefixLenY(mid);
            if (len > EPS_IN) hi = mid;
            else lo = mid;
        }
        tStart = hi;
    }

    // Find first t such that prefixLenY(t) >= 2r
    {
        int lo = 0, hi = LIM;
        const double target = 2.0 * r - EPS_FULL;
        while (lo + 1 < hi) {
            int mid = (lo + hi) / 2;
            double len = prefixLenY(mid);
            if (len >= target) hi = mid;
            else lo = mid;
        }
        tFull = hi;
    }

    int yMinus = tStart - 1;
    int yPlus = tFull;
    int cy = (yMinus + yPlus) / 2;

    it.answer(cx, cy, r);
    return 0;
}