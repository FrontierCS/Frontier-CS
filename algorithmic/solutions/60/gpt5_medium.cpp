#include <bits/stdc++.h>
using namespace std;

static const int LIM = 100000;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    cout.flush();
    double res;
    if (!(cin >> res)) {
        // If input fails, terminate to avoid undefined behavior
        exit(0);
    }
    return res;
}

double query_vertical(int x) {
    return ask(x, 0, x, LIM);
}
double query_horizontal(int y) {
    return ask(0, y, LIM, y);
}

int maximize_on_axis(function<double(int)> f) {
    int l = 0, r = LIM;
    double bestVal = -1.0;
    int bestPos = -1;
    // Ternary search on integer domain
    while (r - l > 3) {
        int m1 = l + (r - l) / 3;
        int m2 = r - (r - l) / 3;
        double v1 = f(m1);
        double v2 = f(m2);
        if (v1 < v2) {
            l = m1;
        } else {
            r = m2;
        }
    }
    for (int i = l; i <= r; ++i) {
        double v = f(i);
        if (v > bestVal) {
            bestVal = v;
            bestPos = i;
        }
    }
    // Refine locally around bestPos
    int L = max(0, bestPos - 3), R = min(LIM, bestPos + 3);
    for (int i = L; i <= R; ++i) {
        double v = f(i);
        if (v > bestVal) {
            bestVal = v;
            bestPos = i;
        }
    }
    return bestPos;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Find cx by maximizing vertical intersection length
    int cx = maximize_on_axis(query_vertical);
    double lenV = query_vertical(cx);

    // Find cy by maximizing horizontal intersection length
    int cy = maximize_on_axis(query_horizontal);
    double lenH = query_horizontal(cy);

    // Radius is half of maximum chord length (2r) -> r = len/2
    // Use both measurements for robustness
    long long r1 = llround(lenV / 2.0);
    long long r2 = llround(lenH / 2.0);
    long long r = (r1 == r2 ? r1 : min(r1, r2)); // in case of tiny discrepancies

    cout << "answer " << cx << ' ' << cy << ' ' << r << '\n';
    cout.flush();
    return 0;
}