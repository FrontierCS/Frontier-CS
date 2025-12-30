#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100000;
const double THRESH = 1e-4;

double query_horiz(int y) {
    cout << "query 0 " << y << " " << MAXN << " " << y << endl << flush;
    double len;
    cin >> len;
    return len;
}

double query_vert(int x) {
    cout << "query " << x << " 0 " << x << " " << MAXN << endl << flush;
    double len;
    cin >> len;
    return len;
}

int find_min_pos(bool is_horiz) {
    int lo = 0, hi = MAXN;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = is_horiz ? query_horiz(mid) : query_vert(mid);
        if (len > THRESH) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

int find_max_pos(bool is_horiz) {
    int lo = 0, hi = MAXN;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = is_horiz ? query_horiz(mid) : query_vert(mid);
        if (len > THRESH) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo;
}

int main() {
    // For y (horizontal queries)
    int low_y = find_min_pos(true);
    int high_y = find_max_pos(true);
    int ry = (high_y - low_y + 2) / 2;
    int cy = (low_y + high_y) / 2;

    // For x (vertical queries)
    int low_x = find_min_pos(false);
    int high_x = find_max_pos(false);
    int rx = (high_x - low_x + 2) / 2;
    int cx = (low_x + high_x) / 2;

    // Use ry and cy, rx should match ry
    int r = ry;
    cout << "answer " << cx << " " << cy << " " << r << endl << flush;
    return 0;
}