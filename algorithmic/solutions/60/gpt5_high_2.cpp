#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 100000;
static const int STEP = 199;
static const long double EPS = 1e-7L;

long double do_query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << endl;
    cout.flush();
    long double v;
    if (!(cin >> v)) {
        exit(0);
    }
    return v;
}

struct AxisResult {
    int coord_int;
    long double r2_est; // estimated r^2 from this axis (average of two measurements)
};

AxisResult find_coord(bool vertical) {
    // Build probing positions with step STEP and include MAXC at the end
    vector<int> positions;
    for (int p = 0; p <= MAXC; p += STEP) positions.push_back(p);
    if (positions.empty() || positions.back() != MAXC) positions.push_back(MAXC);

    int p0 = -1;
    long double L0 = 0;

    // Find first position with non-zero intersection
    for (int p : positions) {
        long double L = vertical ? do_query(p, 0, p, MAXC) : do_query(0, p, MAXC, p);
        if (L > EPS) {
            p0 = p;
            L0 = L;
            break;
        }
    }

    // Should always find due to STEP and r >= 100
    if (p0 == -1) {
        // Fallback (should not happen), just answer center of box with radius 100
        cout << "answer 50000 50000 100" << endl;
        cout.flush();
        exit(0);
    }

    // Find neighbor with non-zero intersection
    int p1 = p0 + 1;
    if (p1 > MAXC) p1 = p0 - 1;
    long double L1 = vertical ? do_query(p1, 0, p1, MAXC) : do_query(0, p1, MAXC, p1);
    if (L1 <= EPS) {
        // Try the other neighbor
        p1 = p0 - 1;
        if (p1 < 0) p1 = p0 + 1;
        L1 = vertical ? do_query(p1, 0, p1, MAXC) : do_query(0, p1, MAXC, p1);
    }

    // In the unlikely case still zero due to numerical issues, move closer to center by trying +/-2
    if (L1 <= EPS) {
        int alt = p0 + 2;
        if (alt <= MAXC) {
            L1 = vertical ? do_query(alt, 0, alt, MAXC) : do_query(0, alt, MAXC, alt);
            if (L1 > EPS) p1 = alt;
        }
    }
    if (L1 <= EPS) {
        int alt = p0 - 2;
        if (alt >= 0) {
            L1 = vertical ? do_query(alt, 0, alt, MAXC) : do_query(0, alt, MAXC, alt);
            if (L1 > EPS) p1 = alt;
        }
    }

    // Compute squared half-chord lengths
    long double s0 = (L0 * 0.5L) * (L0 * 0.5L);
    long double s1 = (L1 * 0.5L) * (L1 * 0.5L);

    // Solve for coord using: (p - c)^2 + s = r^2
    // => 2 (p1 - p0) c = (s1 - s0) + (p1^2 - p0^2)
    long double num = (s1 - s0) + ( (long double)p1 * p1 - (long double)p0 * p0 );
    long double den = 2.0L * ( (long double)p1 - (long double)p0 );
    long double c_est = num / den;

    long long c_int = llround(c_est);
    if (c_int < 0) c_int = 0;
    if (c_int > MAXC) c_int = MAXC;

    // Estimate r^2 from each measurement and average
    long double r2_a = ((long double)p0 - c_est) * ((long double)p0 - c_est) + s0;
    long double r2_b = ((long double)p1 - c_est) * ((long double)p1 - c_est) + s1;
    long double r2_est = 0.5L * (r2_a + r2_b);

    AxisResult res;
    res.coord_int = (int)c_int;
    res.r2_est = r2_est;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Find x-center and r^2 from vertical probes
    AxisResult xr = find_coord(true);

    // Find y-center and r^2 from horizontal probes
    AxisResult yr = find_coord(false);

    // Combine r^2 estimates
    long double r2 = 0.5L * (xr.r2_est + yr.r2_est);
    if (r2 < 0) r2 = 0;
    long long r_int = llround(sqrtl(r2));

    // Output final answer
    cout << "answer " << xr.coord_int << ' ' << yr.coord_int << ' " << r_int << endl;
    cout.flush();
    return 0;
}