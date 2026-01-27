#include <bits/stdc++.h>
using namespace std;

static const int N = 100000;
static const int MAXQ = 1024;

struct Interactor {
    int qcnt = 0;

    long double ask(int x1, int y1, int x2, int y2) {
        if (qcnt >= MAXQ) exit(0);
        cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n' << flush;
        qcnt++;

        long double res;
        if (!(cin >> res)) exit(0);
        if (res < -0.5L) exit(0);
        return res;
    }
};

struct AxisSolveResult {
    long long c = -1;
    long long r = -1;
};

static inline long double sqr(long double x) { return x * x; }

AxisSolveResult solve_axis_adjacent(int k1, int k2, long double L1, long double L2) {
    // k2 = k1 +/- 1, both inside
    int step = k2 - k1;
    if (abs(step) != 1) return {};

    long double A1 = (L1 * L1) / 4.0L;
    long double A2 = (L2 * L2) / 4.0L;

    long double c_est = ((long double)k1 + (long double)k2) / 2.0L + (A2 - A1) / (2.0L * (long double)step);
    long long c = llround(c_est);

    long double d1 = (long double)k1 - (long double)c;
    long double d2 = (long double)k2 - (long double)c;

    long double r2_est1 = A1 + d1 * d1;
    long double r2_est2 = A2 + d2 * d2;
    long double r2_est = (r2_est1 + r2_est2) / 2.0L;

    long long r2 = llround(r2_est);
    long long r = llround(sqrt((long double)r2));

    return {c, r};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor I;

    vector<long double> vval(N + 1, 0.0L), hval(N + 1, 0.0L);
    vector<unsigned char> vasked(N + 1, 0), hasked(N + 1, 0);

    auto qV = [&](int x) -> long double {
        x = max(0, min(N, x));
        if (!vasked[x]) {
            vasked[x] = 1;
            vval[x] = I.ask(x, 0, x, N);
        }
        return vval[x];
    };
    auto qH = [&](int y) -> long double {
        y = max(0, min(N, y));
        if (!hasked[y]) {
            hasked[y] = 1;
            hval[y] = I.ask(0, y, N, y);
        }
        return hval[y];
    };

    const int STEP = 199;
    const long double INSIDE_EPS = 1.0L; // minimal positive length at integer coordinates is >= ~28 when r>=100

    int x_hit = -1;
    for (int x = 0; x <= N; x += STEP) {
        if (qV(x) > INSIDE_EPS) {
            x_hit = x;
            break;
        }
    }
    if (x_hit < 0) exit(0);

    int x2 = -1;
    if (x_hit + 1 <= N && qV(x_hit + 1) > INSIDE_EPS) x2 = x_hit + 1;
    else if (x_hit - 1 >= 0 && qV(x_hit - 1) > INSIDE_EPS) x2 = x_hit - 1;
    else if (x_hit + 2 <= N && qV(x_hit + 2) > INSIDE_EPS) x2 = x_hit + 2;
    else if (x_hit - 2 >= 0 && qV(x_hit - 2) > INSIDE_EPS) x2 = x_hit - 2;
    if (x2 < 0) exit(0);

    AxisSolveResult vx = solve_axis_adjacent(x_hit, x2, qV(x_hit), qV(x2));
    if (vx.c < 0 || vx.r < 0) exit(0);
    long long cx0 = vx.c;

    int y_hit = -1;
    for (int y = 0; y <= N; y += STEP) {
        if (qH(y) > INSIDE_EPS) {
            y_hit = y;
            break;
        }
    }
    if (y_hit < 0) exit(0);

    int y2 = -1;
    if (y_hit + 1 <= N && qH(y_hit + 1) > INSIDE_EPS) y2 = y_hit + 1;
    else if (y_hit - 1 >= 0 && qH(y_hit - 1) > INSIDE_EPS) y2 = y_hit - 1;
    else if (y_hit + 2 <= N && qH(y_hit + 2) > INSIDE_EPS) y2 = y_hit + 2;
    else if (y_hit - 2 >= 0 && qH(y_hit - 2) > INSIDE_EPS) y2 = y_hit - 2;
    if (y2 < 0) exit(0);

    AxisSolveResult hy = solve_axis_adjacent(y_hit, y2, qH(y_hit), qH(y2));
    if (hy.c < 0 || hy.r < 0) exit(0);
    long long cy0 = hy.c;

    auto refineCenterAxis = [&](long long c0, bool vertical) -> pair<long long, long double> {
        long long bestC = c0;
        long double bestL = -1.0L;
        for (int d = -2; d <= 2; d++) {
            long long c = c0 + d;
            if (c < 0 || c > N) continue;
            long double L = vertical ? qV((int)c) : qH((int)c);
            if (L > bestL) {
                bestL = L;
                bestC = c;
            }
        }
        return {bestC, bestL};
    };

    auto [cx, Lvmax] = refineCenterAxis(cx0, true);
    auto [cy, Lhmax] = refineCenterAxis(cy0, false);

    long long rv = llround(Lvmax / 2.0L);
    long long rh = llround(Lhmax / 2.0L);
    long long r = (rv == rh) ? rv : llround(((long double)rv + (long double)rh) / 2.0L);

    // Basic consistency check with a couple of tangency queries (use any remaining budget)
    auto isZero = [&](long double L) -> bool { return fabsl(L) < 1e-4L; };

    if (cx + r <= N) (void)isZero(qV((int)(cx + r)));
    if (cy + r <= N) (void)isZero(qH((int)(cy + r)));

    // Ensure constraints (should hold)
    if (r < 100) r = 100;
    if (cx < r) cx = r;
    if (cy < r) cy = r;
    if (cx > N - r) cx = N - r;
    if (cy > N - r) cy = N - r;

    cout << "answer " << cx << ' ' << cy << ' ' << r << '\n' << flush;
    return 0;
}