#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int BOX = 100000;
    const int STEP = 199;
    const double EPS = 1e-3;

    auto query = [&](int x1, int y1, int x2, int y2) -> double {
        cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << endl;
        cout.flush();
        double res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    // Stage 1: find some y_in where horizontal line intersects disk (len > 0)
    int y_in = -1;
    for (int y = 0; y <= BOX; y += STEP) {
        double len = query(0, y, BOX, y);
        if (len > EPS) {
            y_in = y;
            break;
        }
    }

    if (y_in == -1) {
        // According to problem constraints this should never happen.
        // If it does, terminate.
        return 0;
    }

    // Stage 2: find vertical interval [y_low, y_high] where lines intersect disk
    int y_low, y_high;

    // Find y_low: smallest integer y with positive intersection length
    int lo = 0, hi = y_in;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = query(0, mid, BOX, mid);
        if (len > EPS) hi = mid;
        else lo = mid;
    }
    y_low = hi;

    // Find y_high: largest integer y with positive intersection length
    lo = y_in;
    hi = BOX;
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = query(0, mid, BOX, mid);
        if (len > EPS) lo = mid;
        else hi = mid;
    }
    y_high = lo;

    int Y = (y_low + y_high) / 2;
    int R = y_high - Y + 1;

    // Stage 3: find X using horizontal line through center (y = Y)
    // F(x) = length of intersection of segment from (0,Y) to (x,Y) with disk.
    // It is 0 for x <= X-R, >0 for x >= X-R+1. We find minimal x with F(x) > 0.

    lo = 0;
    hi = BOX; // F(hi) is guaranteed > 0 since it covers whole disk.
    while (hi - lo > 1) {
        int mid = (lo + hi) / 2;
        double len = query(0, Y, mid, Y);
        if (len > EPS) hi = mid;
        else lo = mid;
    }
    int XL = hi - 1; // X - R
    int X = XL + R;

    cout << "answer " << X << ' ' << Y << ' ' << R << endl;
    cout.flush();

    return 0;
}