#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Function to query the interactive judge.
// Sends a query for the line segment from (x1, y1) to (x2, y2).
// Returns the length of the intersection with the disk.
double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    if (!(cin >> res)) exit(0);
    return res;
}

// Function to submit the final answer.
void answer(int x, int y, int r) {
    cout << "answer " << x << " " << y << " " << r << endl;
}

int main() {
    // The box size is 100,000 x 100,000
    int W = 100000;
    
    // Step size for scanning the x-coordinate.
    // The radius r >= 100, so the diameter >= 200.
    // A step size of 120 ensures we will hit the disk at least once.
    int step = 120;
    
    int x_hit = -1;
    double len_hit = 0;
    
    // 1. Scan vertical lines to find any intersection with the disk
    for (int x = 0; x <= W; x += step) {
        // Query the full vertical line at x
        double l = query(x, 0, x, W);
        if (l > 0.5) { // Use a threshold > 0.5 to filter potential noise (though intersections are integers or large)
            x_hit = x;
            len_hit = l;
            break;
        }
    }
    
    // 2. We found one vertical chord. We need a second one to solve for position and radius.
    // We probe the immediate neighbor. Since the disk is at least 200 units wide, 
    // at least one neighbor (left or right) will also intersect significantly.
    int k1 = x_hit;
    double L1 = len_hit;
    
    int k2 = x_hit + 1;
    double L2 = query(k2, 0, k2, W);
    
    // If the right neighbor doesn't intersect (or barely touches), try the left neighbor.
    if (L2 < 0.5) {
        k2 = x_hit - 1;
        L2 = query(k2, 0, k2, W);
    }
    
    // 3. Calculate xc (center x-coordinate) and r (radius)
    // We have two chord lengths L1 at k1 and L2 at k2.
    // The half-chord length squared is: (L/2)^2 = r^2 - (k - xc)^2
    // Let v = (L/2)^2.
    // v1 = r^2 - (k1 - xc)^2
    // v2 = r^2 - (k2 - xc)^2
    // Subtracting the two equations:
    // v1 - v2 = (k2 - xc)^2 - (k1 - xc)^2
    // v1 - v2 = (k2 - k1) * (k2 + k1 - 2*xc)
    // 2*xc = k1 + k2 - (v1 - v2) / (k2 - k1)
    
    double v1 = (L1 / 2.0) * (L1 / 2.0);
    double v2 = (L2 / 2.0) * (L2 / 2.0);
    
    double term = (v1 - v2) / (double)(k2 - k1);
    double xc_val = (k1 + k2 - term) / 2.0;
    int xc = (int)round(xc_val);
    
    // Calculate r from one of the equations
    double r2 = v1 + pow(k1 - xc, 2);
    int r = (int)round(sqrt(r2));
    
    // 4. Find yc (center y-coordinate) using binary search
    // We know the vertical line at x=xc intersects the disk from y = yc - r to y = yc + r.
    // We query the segment from (xc, 0) to (xc, Y).
    // The result will be 0 if Y <= yc - r.
    // The result will be positive if Y > yc - r.
    // Specifically, for integer Y, the first Y with non-zero intersection length (length 1)
    // will be Y = yc - r + 1.
    
    int low = 0;
    int high = W;
    
    while (high - low > 1) {
        int mid = (low + high) / 2;
        // Query segment from (xc, 0) to (xc, mid)
        double res = query(xc, 0, xc, mid);
        if (res > 0.5) {
            high = mid;
        } else {
            low = mid;
        }
    }
    
    // high is the first index where the query returns a non-zero length.
    // Intersection starts at yc - r. 
    // query(..., high) covers [0, high]. Intersection with [yc-r, yc+r] is [yc-r, high].
    // Length is high - (yc - r).
    // For the first positive integer result (which is 1), high - (yc - r) = 1.
    // So yc = high - 1 + r.
    
    int yc = high - 1 + r;
    
    answer(xc, yc, r);
    
    return 0;
}