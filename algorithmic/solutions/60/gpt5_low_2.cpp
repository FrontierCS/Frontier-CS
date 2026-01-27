#include <bits/stdc++.h>
using namespace std;

static const int BOX = 100000;
static const int MAX_Q = 1024;
static const double EPS = 1e-9;

long double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    long double resp = 0.0L;
    if (!(cin >> resp)) {
        // If interaction fails, exit to avoid undefined behavior
        exit(0);
    }
    return resp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto get_vertical_info = [&]() -> tuple<long double,long double> {
        int step = 200;
        int x0 = -1;
        long double L0 = 0.0L;
        for (int x = 0; x <= BOX; x += step) {
            long double L = query(x, 0, x, BOX);
            if (L > EPS) {
                x0 = x; L0 = L;
                break;
            }
        }
        if (x0 == -1) {
            // fallback with smaller step
            step = 100;
            for (int x = 0; x <= BOX; x += step) {
                long double L = query(x, 0, x, BOX);
                if (L > EPS) {
                    x0 = x; L0 = L;
                    break;
                }
            }
        }
        // Ensure we found something
        if (x0 == -1) {
            // As a last resort (should not happen), answer center (0,0) r 0
            cout << "answer 0 0 0" << endl;
            cout.flush();
            return {0,0};
        }
        int delta = 50;
        int x1 = -1;
        long double L1 = 0.0L;
        if (x0 + delta <= BOX) {
            long double t = query(x0 + delta, 0, x0 + delta, BOX);
            if (t > EPS) { x1 = x0 + delta; L1 = t; }
        }
        if (x1 == -1 && x0 - delta >= 0) {
            long double t = query(x0 - delta, 0, x0 - delta, BOX);
            if (t > EPS) { x1 = x0 - delta; L1 = t; }
        }
        // If still failed (pathological), try expanding search around x0
        if (x1 == -1) {
            for (int d = 1; d <= 100; ++d) {
                if (x0 + d <= BOX) {
                    long double t = query(x0 + d, 0, x0 + d, BOX);
                    if (t > EPS) { x1 = x0 + d; L1 = t; break; }
                }
                if (x0 - d >= 0) {
                    long double t = query(x0 - d, 0, x0 - d, BOX);
                    if (t > EPS) { x1 = x0 - d; L1 = t; break; }
                }
            }
        }
        if (x1 == -1) {
            cout << "answer 0 0 0" << endl;
            cout.flush();
            return {0,0};
        }
        long double a0 = (L0 * 0.5L) * (L0 * 0.5L);
        long double a1 = (L1 * 0.5L) * (L1 * 0.5L);
        long double num = ((long double)x1 * (long double)x1 - (long double)x0 * (long double)x0) - (a1 - a0);
        long double den = 2.0L * ((long double)x1 - (long double)x0);
        long double cx = num / den;
        long double r2 = a0 + ((long double)x0 - cx)*((long double)x0 - cx);
        long double r = sqrt(max((long double)0.0, r2));
        return {cx, r};
    };

    auto get_horizontal_info = [&]() -> tuple<long double,long double> {
        int step = 200;
        int y0 = -1;
        long double L0 = 0.0L;
        for (int y = 0; y <= BOX; y += step) {
            long double L = query(0, y, BOX, y);
            if (L > EPS) {
                y0 = y; L0 = L;
                break;
            }
        }
        if (y0 == -1) {
            // fallback with smaller step
            step = 100;
            for (int y = 0; y <= BOX; y += step) {
                long double L = query(0, y, BOX, y);
                if (L > EPS) {
                    y0 = y; L0 = L;
                    break;
                }
            }
        }
        if (y0 == -1) {
            cout << "answer 0 0 0" << endl;
            cout.flush();
            return {0,0};
        }
        int delta = 50;
        int y1 = -1;
        long double L1 = 0.0L;
        if (y0 + delta <= BOX) {
            long double t = query(0, y0 + delta, BOX, y0 + delta);
            if (t > EPS) { y1 = y0 + delta; L1 = t; }
        }
        if (y1 == -1 && y0 - delta >= 0) {
            long double t = query(0, y0 - delta, BOX, y0 - delta);
            if (t > EPS) { y1 = y0 - delta; L1 = t; }
        }
        if (y1 == -1) {
            for (int d = 1; d <= 100; ++d) {
                if (y0 + d <= BOX) {
                    long double t = query(0, y0 + d, BOX, y0 + d);
                    if (t > EPS) { y1 = y0 + d; L1 = t; break; }
                }
                if (y0 - d >= 0) {
                    long double t = query(0, y0 - d, BOX, y0 - d);
                    if (t > EPS) { y1 = y0 - d; L1 = t; break; }
                }
            }
        }
        if (y1 == -1) {
            cout << "answer 0 0 0" << endl;
            cout.flush();
            return {0,0};
        }
        long double a0 = (L0 * 0.5L) * (L0 * 0.5L);
        long double a1 = (L1 * 0.5L) * (L1 * 0.5L);
        long double num = ((long double)y1 * (long double)y1 - (long double)y0 * (long double)y0) - (a1 - a0);
        long double den = 2.0L * ((long double)y1 - (long double)y0);
        long double cy = num / den;
        long double r2 = a0 + ((long double)y0 - cy)*((long double)y0 - cy);
        long double r = sqrt(max((long double)0.0, r2));
        return {cy, r};
    };

    auto [cx_est, r_from_v] = get_vertical_info();
    auto [cy_est, r_from_h] = get_horizontal_info();

    // Combine radii (average) and round to integers as per problem constraints
    long double r_est = (r_from_v + r_from_h) * 0.5L;

    long long cx = llround(cx_est);
    long long cy = llround(cy_est);
    long long r  = llround(r_est);

    // Clamp just in case
    cx = max(0LL, min((long long)BOX, cx));
    cy = max(0LL, min((long long)BOX, cy));
    r = max(0LL, r);

    cout << "answer " << cx << " " << cy << " " << r << endl;
    cout.flush();
    return 0;
}