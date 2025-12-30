#include <bits/stdc++.h>
using namespace std;

const double INF_COORD = 1e12;
const int MAX_A = 10000;
const int MAX_B = 10000;

// Parameters for binary search
const double Y_START = -15000.0;
const double Y_END   =  15000.0;
const double EPS_JUMP = 1e-6;      // threshold to detect derivative change
const double EPS_A    = 1e-3;      // tolerance for |a| comparison
const double SMALL   = 1e-6;       // small offset for derivative computation

int Q_count = 0;  // number of queries made
int N;            // number of lines

// Cache for queries: map from (x, y) to S(x, y)
map<pair<double, double>, double> cache;

double query(double x, double y) {
    // Ensure point is inside the territory
    if (x < -INF_COORD || x > INF_COORD || y < -INF_COORD || y > INF_COORD) {
        cerr << "Query point out of bounds!" << endl;
        exit(1);
    }
    auto key = make_pair(x, y);
    if (cache.count(key)) return cache[key];
    if (Q_count >= 10000) {
        cerr << "Too many queries!" << endl;
        exit(1);
    }
    cout << "? " << fixed << setprecision(12) << x << " " << y << endl;
    double res;
    cin >> res;
    cache[key] = res;
    Q_count++;
    return res;
}

// Compute derivative at (x, y) using central difference with given epsilon
double derivative(double x, double y, double eps = SMALL) {
    double left = query(x, y - eps);
    double right = query(x, y + eps);
    return (right - left) / (2.0 * eps);
}

// Find all kinks (points where derivative jumps) for a given x.
// Returns vector of (y, jump_size) for exactly N lines.
vector<pair<double, double>> find_kinks(double x) {
    vector<pair<double, double>> kinks;
    // Initial leftmost point
    double y = Y_START;
    double S_y = query(x, y);
    // Use a small step to estimate leftmost derivative
    double step_init = 1.0;
    double y1 = y + step_init;
    double S_y1 = query(x, y1);
    double D = (S_y1 - S_y) / step_init;   // current derivative
    y = y1;