#include <bits/stdc++.h>
using namespace std;

const double EPS = 1e-5;
const int MAX = 100000;

double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    cin >> res;
    return res;
}

int find_left() {
    int lo = 0, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query(mid, 0, mid, MAX);
        if (len > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo; // Lpos
}

int find_right(int left_pos) {
    int lo = left_pos, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query(mid, 0, mid, MAX);
        if (len > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo; // Rpos
}

int find_bottom() {
    int lo = 0, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query(0, mid, MAX, mid);
        if (len > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo; // Bpos
}

int find_top(int bottom_pos) {
    int lo = bottom_pos, hi = MAX;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query(0, mid, MAX, mid);
        if (len > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo; // Tpos
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int Lpos = find_left();
    int Rpos = find_right(Lpos);
    int x = (Lpos + Rpos) / 2;
    int r_vert = (Rpos - Lpos + 2) / 2;

    int Bpos = find_bottom();
    int Tpos = find_top(Bpos);
    int y = (Bpos + Tpos) / 2;
    int r_horiz = (Tpos - Bpos + 2) / 2;

    // r_vert and r_horiz should be equal; we choose r_vert.
    cout << "answer " << x << " " << y << " " << r_vert << endl;

    return 0;
}