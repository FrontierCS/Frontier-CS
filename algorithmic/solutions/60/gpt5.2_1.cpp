#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 100000;
static const int STEP = 199;
static const long double EPS = 1e-3L;

struct Hit {
    int k;
    long double L;
    long long s; // (L/2)^2 rounded to integer
};

static int qcnt = 0;

static long double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
    cout.flush();
    qcnt++;
    long double res;
    if (!(cin >> res)) exit(0);
    return res;
}

static long long chordS(long double L) {
    long double h = L * 0.5L;
    long double s = h * h;
    return llround(s);
}

static long long isqrt_ll(long long n) {
    if (n <= 0) return 0;
    long long r = (long long) floor(sqrt((long double)n));
    while ((r + 1) > 0 && (__int128)(r + 1) * (r + 1) <= n) r++;
    while ((__int128)r * r > n) r--;
    return r;
}

static long long div_exact(__int128 a, __int128 b) {
    // b != 0, division is exact
    if (b < 0) a = -a, b = -b;
    // C++ division truncates toward 0; exact division avoids issues.
    __int128 q = a / b;
    return (long long)q;
}

static Hit firstPositiveVertical() {
    for (int x = 0; x <= MAXC; x += STEP) {
        long double L = ask(x, 0, x, MAXC);
        if (L > EPS) return {x, L, chordS(L)};
    }
    exit(0);
}

static Hit firstPositiveHorizontal() {
    for (int y = 0; y <= MAXC; y += STEP) {
        long double L = ask(0, y, MAXC, y);
        if (L > EPS) return {y, L, chordS(L)};
    }
    exit(0);
}

static Hit neighborPositiveVertical(int x0) {
    if (x0 + 1 <= MAXC) {
        long double L = ask(x0 + 1, 0, x0 + 1, MAXC);
        if (L > EPS) return {x0 + 1, L, chordS(L)};
    }
    if (x0 - 1 >= 0) {
        long double L = ask(x0 - 1, 0, x0 - 1, MAXC);
        if (L > EPS) return {x0 - 1, L, chordS(L)};
    }
    exit(0);
}

static Hit neighborPositiveHorizontal(int y0) {
    if (y0 + 1 <= MAXC) {
        long double L = ask(0, y0 + 1, MAXC, y0 + 1);
        if (L > EPS) return {y0 + 1, L, chordS(L)};
    }
    if (y0 - 1 >= 0) {
        long double L = ask(0, y0 - 1, MAXC, y0 - 1);
        if (L > EPS) return {y0 - 1, L, chordS(L)};
    }
    exit(0);
}

static pair<long long,long long> solveCenterAndR2FromTwoHits(const Hit& h1, const Hit& h2) {
    long long k1 = h1.k, k2 = h2.k;
    long long s1 = h1.s, s2 = h2.s;

    __int128 k1sq = (__int128)k1 * k1;
    __int128 k2sq = (__int128)k2 * k2;
    __int128 num = (k1sq - k2sq) - (__int128)(s2 - s1);
    __int128 den = (__int128)2 * (k1 - k2);
    long long c = div_exact(num, den);

    long long dk = k1 - c;
    long long r2 = s1 + dk * dk;
    return {c, r2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Hit hx0 = firstPositiveVertical();
    Hit hx1 = neighborPositiveVertical(hx0.k);

    auto [xc, r2x] = solveCenterAndR2FromTwoHits(hx0, hx1);
    long long r = isqrt_ll(r2x);
    if (r * r != r2x) {
        // adjust if needed (should not happen)
        if ((r + 1) * (r + 1) == r2x) r++;
        else if ((r - 1) >= 0 && (r - 1) * (r - 1) == r2x) r--;
    }

    Hit hy0 = firstPositiveHorizontal();
    Hit hy1 = neighborPositiveHorizontal(hy0.k);

    auto [yc, r2y] = solveCenterAndR2FromTwoHits(hy0, hy1);
    (void)r2y; // expected to match r2x

    cout << "answer " << xc << " " << yc << " " << r << "\n";
    cout.flush();
    return 0;
}