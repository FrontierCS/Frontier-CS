#include <bits/stdc++.h>
using namespace std;

const int N = 100000;
const int STEP = 199;
const int DELTA = 50;
const double EPS = 1e-7;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
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

    // Horizontal scan to find y0 with positive intersection
    int y0 = -1;
    double L0 = 0.0;
    for (int i = 0; i * STEP <= N; ++i) {
        int y = i * STEP;
        double len = ask(0, y, N, y);
        if (len > EPS) {
            y0 = y;
            L0 = len;
            break;
        }
    }
    if (y0 == -1) {
        // Fallback (should never happen under constraints)
        cout << "answer 50000 50000 100\n";
        cout.flush();
        return 0;
    }

    // Second horizontal near y0
    int y1 = -1;
    double L1 = 0.0;
    int candYs[2] = { y0 + DELTA, y0 - DELTA };
    for (int k = 0; k < 2; ++k) {
        int y = candYs[k];
        if (y < 0 || y > N) continue;
        double len = ask(0, y, N, y);
        if (len > EPS) {
            y1 = y;
            L1 = len;
            break;
        }
    }
    if (y1 == -1) {
        // Robust fallback: local search (theoretically unnecessary)
        for (int d = 1; d <= 100 && y1 == -1; ++d) {
            for (int sgn = -1; sgn <= 1 && y1 == -1; sgn += 2) {
                int y = y0 + sgn * d;
                if (y < 0 || y > N) continue;
                double len = ask(0, y, N, y);
                if (len > EPS) {
                    y1 = y;
                    L1 = len;
                    break;
                }
            }
        }
    }
    if (y1 == -1) {
        cout << "answer 50000 50000 100\n";
        cout.flush();
        return 0;
    }

    if (y1 == y0) y1 += 1;
    if (y1 < y0) {
        swap(y0, y1);
        swap(L0, L1);
    }

    // Compute cy from two horizontals
    double num_cy = (L1 * L1 - L0 * L0) / 4.0 - (double)y0 * y0 + (double)y1 * y1;
    double den_cy = 2.0 * (y1 - y0);
    double cy_est = num_cy / den_cy;
    long long cy_ll = llround(cy_est);
    if (cy_ll < 0) cy_ll = 0;
    if (cy_ll > N) cy_ll = N;
    double cy = (double)cy_ll;

    // Radius from horizontals
    double r2h0 = (cy - y0) * (cy - y0) + 0.25 * L0 * L0;
    double r2h1 = (cy - y1) * (cy - y1) + 0.25 * L1 * L1;
    double r2h = 0.5 * (r2h0 + r2h1);
    if (r2h < 0) r2h = 0;
    double rh_est = sqrt(r2h);
    long long rh_ll = llround(rh_est);
    if (rh_ll < 100) rh_ll = 100;
    if (rh_ll > N / 2) rh_ll = N / 2;
    double rh = (double)rh_ll;

    // Vertical scan to find x0 with positive intersection
    int x0 = -1;
    double Lv0 = 0.0;
    for (int i = 0; i * STEP <= N; ++i) {
        int x = i * STEP;
        double len = ask(x, 0, x, N);
        if (len > EPS) {
            x0 = x;
            Lv0 = len;
            break;
        }
    }
    if (x0 == -1) {
        cout << "answer " << (N / 2) << ' ' << cy_ll << ' ' << rh_ll << '\n';
        cout.flush();
        return 0;
    }

    // Second vertical near x0
    int x1 = -1;
    double Lv1 = 0.0;
    int candXs[2] = { x0 + DELTA, x0 - DELTA };
    for (int k = 0; k < 2; ++k) {
        int x = candXs[k];
        if (x < 0 || x > N) continue;
        double len = ask(x, 0, x, N);
        if (len > EPS) {
            x1 = x;
            Lv1 = len;
            break;
        }
    }
    if (x1 == -1) {
        // Robust fallback: local search (theoretically unnecessary)
        for (int d = 1; d <= 100 && x1 == -1; ++d) {
            for (int sgn = -1; sgn <= 1 && x1 == -1; sgn += 2) {
                int x = x0 + sgn * d;
                if (x < 0 || x > N) continue;
                double len = ask(x, 0, x, N);
                if (len > EPS) {
                    x1 = x;
                    Lv1 = len;
                    break;
                }
            }
        }
    }
    if (x1 == -1) {
        cout << "answer " << (N / 2) << ' ' << cy_ll << ' ' << rh_ll << '\n';
        cout.flush();
        return 0;
    }

    if (x1 == x0) x1 += 1;
    if (x1 < x0) {
        swap(x0, x1);
        swap(Lv0, Lv1);
    }

    // Compute cx from two verticals
    double num_cx = (Lv1 * Lv1 - Lv0 * Lv0) / 4.0 - (double)x0 * x0 + (double)x1 * x1;
    double den_cx = 2.0 * (x1 - x0);
    double cx_est = num_cx / den_cx;
    long long cx_ll = llround(cx_est);
    if (cx_ll < 0) cx_ll = 0;
    if (cx_ll > N) cx_ll = N;
    double cx = (double)cx_ll;

    // Radius from verticals
    double r2v0 = (cx - x0) * (cx - x0) + 0.25 * Lv0 * Lv0;
    double r2v1 = (cx - x1) * (cx - x1) + 0.25 * Lv1 * Lv1;
    double r2v = 0.5 * (r2v0 + r2v1);
    if (r2v < 0) r2v = 0;
    double rv_est = sqrt(r2v);
    long long rv_ll = llround(rv_est);
    if (rv_ll < 100) rv_ll = 100;
    if (rv_ll > N / 2) rv_ll = N / 2;
    double rv = (double)rv_ll;

    long long r_ll = llround((rh + rv) / 2.0);
    if (r_ll < 100) r_ll = 100;
    if (r_ll > N / 2) r_ll = N / 2;

    cout << "answer " << cx_ll << ' ' << cy_ll << ' ' << r_ll << '\n';
    cout.flush();
    return 0;
}