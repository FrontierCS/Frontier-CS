#include <bits/stdc++.h>
using namespace std;

const int SZ = 100000;
const double EPS = 1e-5;

double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    cin >> res;
    return res;
}

double query_v(int x) {
    return query(x, 0, x, SZ);
}

double query_h(int y) {
    return query(0, y, SZ, y);
}

int find_left_x() {
    int lo = 0, hi = SZ;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        double l = query_v(mid);
        if (l > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

int find_right_x() {
    int lo = 0, hi = SZ;
    while (lo < hi) {
        int mid = lo + (hi - lo + 1) / 2;
        double l = query_v(mid);
        if (l > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo;
}

int find_bottom_y() {
    int lo = 0, hi = SZ;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        double l = query_h(mid);
        if (l > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

int find_top_y() {
    int lo = 0, hi = SZ;
    while (lo < hi) {
        int mid = lo + (hi - lo + 1) / 2;
        double l = query_h(mid);
        if (l > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo;
}

int main() {
    int lx = find_left_x();
    int rx = find_right_x();
    int cx = (lx + rx) / 2;
    int r_x = (rx - lx) / 2 + 1;

    int by = find_bottom_y();
    int ty = find_top_y();
    int cy = (by + ty) / 2;
    int r_y = (ty - by) / 2 + 1;

    int r = r_x;  // or r_y, they should match

    cout << "answer " << cx << " " << cy << " " << r << endl;
    return 0;
}