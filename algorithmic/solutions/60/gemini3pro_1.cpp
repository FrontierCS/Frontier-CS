#include <iostream>
#include <cmath>
#include <algorithm>
#include <vector>

using namespace std;

// Function to perform a query
// Returns the length of the segment inside the disk
double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    cin >> res;
    return res;
}

// Function to calculate center coordinate from two measurements at adjacent positions
// Based on the formula derived from chord lengths of a circle:
// If we have two chords of length l1 and l2 at positions p1 and p2 (where p is distance from center),
// and p2 = p1 + 1, we can solve for the center coordinate c.
// l^2 = 4r^2 - 4(p - c)^2
int solve_center(int p1, double l1, int p2, double l2) {
    // Formula: center = (p1 + p2)/2 - (l1^2 - l2^2)/(8*(p2 - p1))
    double term1 = (double)(p1 + p2) / 2.0;
    double num = l1 * l1 - l2 * l2;
    double den = 8.0 * (p2 - p1);
    double c = term1 - num / den;
    return (int)round(c);
}

int main() {
    // 1. Find the x-coordinate of the center (xc)
    // The disk has radius r >= 100, so its diameter is >= 200.
    // The intersection of the disk with vertical lines will be non-zero for x in (xc - r, xc + r).
    // The length of integer coordinates with non-zero intersection is at least 2*r - 1 >= 199.
    // By scanning with a step of 199, we are guaranteed to find at least one x inside the disk.
    int x_hit = -1;
    double l_x = 0;
    
    // Scan range covers all possible valid x coordinates for the disk center
    for (int x = 100; x <= 99900; x += 199) {
        double res = query(x, 0, x, 100000);
        if (res > 1e-6) {
            x_hit = x;
            l_x = res;
            break;
        }
    }
    
    // If we somehow didn't hit (should not happen given constraints), we'd need a fallback,
    // but the loop covers the box sufficiently.

    // 2. Refine xc using a neighbor point
    // We need two points to calculate the center.
    int x_neighbor = x_hit + 1;
    double l_x_neighbor = query(x_neighbor, 0, x_neighbor, 100000);
    
    int xc;
    // If the right neighbor is inside the disk
    if (l_x_neighbor > 1e-6) {
        xc = solve_center(x_hit, l_x, x_neighbor, l_x_neighbor);
    } else {
        // Otherwise, the left neighbor must be inside
        x_neighbor = x_hit - 1;
        l_x_neighbor = query(x_neighbor, 0, x_neighbor, 100000);
        xc = solve_center(x_hit, l_x, x_neighbor, l_x_neighbor);
    }
    
    // 3. Find the radius (r)
    // A vertical line passing through the exact center xc will define a diameter of the circle.
    double l_center = query(xc, 0, xc, 100000);
    int r = (int)round(l_center / 2.0);
    
    // 4. Find the y-coordinate of the center (yc)
    // Now that we know r, we can optimize the scanning step for y.
    // The valid interval has length roughly 2r. We can step by roughly 2r.
    // We use a safe margin to ensure we hit integer coordinates inside the circle.
    int step_y = max(199, 2 * r - 50);
    int y_hit = -1;
    double l_y = 0;
    
    for (int y = 100; y <= 99900; y += step_y) {
        double res = query(0, y, 100000, y);
        if (res > 1e-6) {
            y_hit = y;
            l_y = res;
            break;
        }
    }
    
    // 5. Refine yc
    int y_neighbor = y_hit + 1;
    double l_y_neighbor = query(0, y_neighbor, 100000, y_neighbor);
    int yc;
    
    if (l_y_neighbor > 1e-6) {
        yc = solve_center(y_hit, l_y, y_neighbor, l_y_neighbor);
    } else {
        y_neighbor = y_hit - 1;
        l_y_neighbor = query(0, y_neighbor, 100000, y_neighbor);
        yc = solve_center(y_hit, l_y, y_neighbor, l_y_neighbor);
    }
    
    // Output answer
    cout << "answer " << xc << " " << yc << " " << r << endl;
    
    return 0;
}