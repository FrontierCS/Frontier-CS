#include <iostream>
#include <iomanip>
#include <cmath>
#include <algorithm>
using namespace std;

const double EPS = 1e-4;
const int MAX = 100000;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double len;
    cin >> len;
    return len;
}

int main() {
    // Find x boundaries
    int Lp, Rp;
    int lo, hi;

    // First positive vertical
    lo = 0, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = ask(mid, 0, mid, MAX);
        if (len > EPS) hi = mid;
        else lo = mid + 1;
    }
    Lp = lo;

    // Last positive vertical
    lo = Lp, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = ask(mid, 0, mid, MAX);
        if (len > EPS) lo = mid;
        else hi = mid - 1;
    }
    Rp = lo;

    int L0 = Lp - 1;
    int R0 = Rp + 1;
    int x0 = (L0 + R0) / 2;
    int r_x = (R0 - L0) / 2;

    // Find y boundaries
    int Bp, Tp;
    // First positive horizontal
    lo = 0, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = ask(0, mid, MAX, mid);
        if (len > EPS) hi = mid;
        else lo = mid + 1;
    }
    Bp = lo;

    // Last positive horizontal
    lo = Bp, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = ask(0, mid, MAX, mid);
        if (len > EPS) lo = mid;
        else hi = mid - 1;
    }
    Tp = lo;

    int B0 = Bp - 1;
    int T0 = Tp + 1;
    int y0 = (B0 + T0) / 2;
    int r_y = (T0 - B0) / 2;

    // Output answer (r_x and r_y should be equal)
    cout << "answer " << x0 << " " << y0 << " " << r_x << endl;
    cout.flush();

    return 0;
}