#include <iostream>
#include <cmath>
#include <algorithm>
using namespace std;

const int MAX_COORD = 100000;
const double THRESHOLD = 0.5;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double res;
    cin >> res;
    return res;
}

int main() {
    // Binary search for left boundary (x)
    int lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = ask(mid, 0, mid, MAX_COORD);
        if (len > THRESHOLD) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int left_x = lo;

    // Binary search for right boundary (x)
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = ask(mid, 0, mid, MAX_COORD);
        if (len > THRESHOLD) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    int right_x = lo;

    // Binary search for bottom boundary (y)
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = ask(0, mid, MAX_COORD, mid);
        if (len > THRESHOLD) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int bottom_y = lo;

    // Binary search for top boundary (y)
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = ask(0, mid, MAX_COORD, mid);
        if (len > THRESHOLD) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    int top_y = lo;

    // Compute center and radius
    int x = (left_x + right_x) / 2;
    int y = (bottom_y + top_y) / 2;
    int r = (right_x - left_x + 2) / 2;

    // Output answer
    cout << "answer " << x << " " << y << " " << r << endl;
    cout.flush();

    return 0;
}