#include <iostream>
#include <iomanip>
#include <cmath>
using namespace std;

const int MAX_COORD = 100000;
const double EPS = 1e-4;

double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double resp;
    cin >> resp;
    return resp;
}

int main() {
    int x_first, x_last, y_first, y_last;
    
    // Find first x where vertical chord is positive
    int lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query(mid, 0, mid, MAX_COORD);
        if (len > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    x_first = lo;
    
    // Find last x where vertical chord is positive
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query(mid, 0, mid, MAX_COORD);
        if (len > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    x_last = lo;
    
    // Find first y where horizontal chord is positive
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        double len = query(0, mid, MAX_COORD, mid);
        if (len > EPS) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    y_first = lo;
    
    // Find last y where horizontal chord is positive
    lo = 0, hi = MAX_COORD;
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        double len = query(0, mid, MAX_COORD, mid);
        if (len > EPS) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    y_last = lo;
    
    int cx = (x_first + x_last) / 2;
    int cy = (y_first + y_last) / 2;
    int r = (x_last - x_first) / 2 + 1;  // also equals (y_last - y_first)/2 + 1
    
    cout << "answer " << cx << " " << cy << " " << r << endl;
    
    return 0;
}