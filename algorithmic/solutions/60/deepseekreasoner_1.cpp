#include <iostream>
#include <iomanip>
#include <cmath>
using namespace std;

double query_vertical(int x) {
    cout << "query " << x << " 0 " << x << " 100000" << endl;
    double res;
    cin >> res;
    return res;
}

double query_horizontal(int y) {
    cout << "query 0 " << y << " 100000 " << y << endl;
    double res;
    cin >> res;
    return res;
}

int main() {
    // Find left boundary xL
    int lo = 0, hi = 100000;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query_vertical(mid);
        if (len > 0.5) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int xL = lo;

    // Find right boundary xR
    lo = 0, hi = 100000;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query_vertical(mid);
        if (len > 0.5) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    int xR = lo;

    // Find bottom boundary yB
    lo = 0, hi = 100000;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query_horizontal(mid);
        if (len > 0.5) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int yB = lo;

    // Find top boundary yT
    lo = 0, hi = 100000;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query_horizontal(mid);
        if (len > 0.5) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    int yT = lo;

    int x0 = (xL + xR) / 2;
    int y0 = (yB + yT) / 2;
    int r = (xR - xL) / 2 + 1;

    cout << "answer " << x0 << " " << y0 << " " << r << endl;

    return 0;
}