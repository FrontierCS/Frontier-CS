#include <bits/stdc++.h>
using namespace std;

double query_horiz(int y) {
    cout << "query 0 " << y << " 100000 " << y << endl;
    double l;
    cin >> l;
    return l;
}

double query_vert(int x) {
    cout << "query " << x << " 0 " << x << " 100000" << endl;
    double l;
    cin >> l;
    return l;
}

bool is_positive_h(int y) {
    return query_horiz(y) > 1e-4;
}

bool is_positive_v(int x) {
    return query_vert(x) > 1e-4;
}

int find_left(bool ( *pos)(int)) {
    int low = 0, high = 100000;
    while (low < high) {
        int mid = low + (high - low) / 2;
        if (pos(mid)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int find_right(bool ( *pos)(int)) {
    int low = 0, high = 100000;
    while (low < high) {
        int mid = low + (high - low + 1) / 2;
        if (pos(mid)) {
            low = mid;
        } else {
            high = mid - 1;
        }
    }
    return low;
}

int main() {
    int yL = find_left(is_positive_h);
    int yR = find_right(is_positive_h);
    int cy = (yL + yR) / 2;
    int diff_y = yR - yL;
    int r = diff_y / 2 + 1;

    int xL = find_left(is_positive_v);
    int xR = find_right(is_positive_v);
    int cx = (xL + xR) / 2;
    int diff_x = xR - xL;
    // Verify r matches, but proceed with y's r

    cout << "answer " << cx << " " << cy << " " << r << endl;
    return 0;
}