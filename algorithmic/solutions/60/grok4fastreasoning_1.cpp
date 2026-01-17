#include <bits/stdc++.h>
using namespace std;

const int N = 100000;
const double EPS = 1e-4;

double query(int x1, int y1, int x2, int y2) {
    if (x1 == x2 && y1 == y2) return 0.0;
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double res;
    cin >> res;
    return res;
}

int find_min_y() {
    int low = 0, high = N;
    while (low < high) {
        int mid = (low + high) / 2;
        double len = query(0, mid, N, mid);
        if (len > EPS) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int find_max_y() {
    int low = 0, high = N;
    while (low < high) {
        int mid = (low + high + 1) / 2;
        double len = query(0, mid, N, mid);
        if (len > EPS) {
            low = mid;
        } else {
            high = mid - 1;
        }
    }
    return low;
}

int find_min_x(int cy) {
    int low = 0, high = N;
    while (low < high) {
        int mid = (low + high) / 2;
        double len = query(0, cy, mid, cy);
        if (len > EPS) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

int main() {
    int y_low = find_min_y();
    int y_high = find_max_y();
    int cy = (y_low + y_high) / 2;
    int r = (y_high - y_low) / 2 + 1;
    int x_min = find_min_x(cy);
    int cx = (x_min - 1) + r;
    cout << "answer " << cx << " " << cy << " " << r << endl;
    cout.flush();
    return 0;
}