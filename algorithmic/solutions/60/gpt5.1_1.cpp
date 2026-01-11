#include <bits/stdc++.h>
using namespace std;

long double do_query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    cout.flush();
    long double res;
    if (!(cin >> res)) {
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int MAXC = 100000;
    const int STEP = 199;
    const long double POS_EPS = 1e-3L;

    // Step 1: Find some vertical line intersecting the disk
    int positive_x = -1;
    for (int x = 0; x <= MAXC; x += STEP) {
        long double len = do_query(x, 0, x, MAXC);
        if (len > POS_EPS) {
            positive_x = x;
            break;
        }
    }
    if (positive_x == -1) {
        // Should not happen given problem constraints
        positive_x = MAXC / 2;
    }

    // Step 2: Binary search for left boundary (x = Xc - R)
    int left_zero = 0;         // g(0) = 0 (circle is inside the box)
    int right_pos = positive_x; // g(positive_x) > 0
    while (right_pos - left_zero > 1) {
        int mid = (left_zero + right_pos) / 2;
        long double len = do_query(mid, 0, mid, MAXC);
        if (len > POS_EPS) right_pos = mid;
        else left_zero = mid;
    }
    int Xleft = right_pos - 1; // = Xc - R

    // Step 3: Binary search for right boundary (x = Xc + R)
    int left_pos = positive_x; // g(positive_x) > 0
    int right_zero = MAXC;     // g(MAXC) = 0
    while (right_zero - left_pos > 1) {
        int mid = (left_pos + right_zero) / 2;
        long double len = do_query(mid, 0, mid, MAXC);
        if (len > POS_EPS) left_pos = mid;
        else right_zero = mid;
    }
    int Xright = right_zero; // = Xc + R

    int Xcenter = (Xleft + Xright) / 2;
    int R = (Xright - Xleft) / 2;

    // Step 4: Binary search for Yc - R along the center vertical line x = Xcenter
    int low = 0;
    int high = MAXC; // segment [0, high], at high=100000 it definitely intersects (full diameter)
    while (high - low > 1) {
        int mid = (low + high) / 2;
        long double len = do_query(Xcenter, 0, Xcenter, mid);
        if (len > POS_EPS) high = mid;  // mid above bottom of disk
        else low = mid;                 // mid at or below bottom of disk
    }
    int YminusR = high - 1; // since high is the smallest integer with positive length
    int Ycenter = YminusR + R;

    cout << "answer " << Xcenter << ' ' << Ycenter << ' ' << R << '\n';
    cout.flush();
    return 0;
}