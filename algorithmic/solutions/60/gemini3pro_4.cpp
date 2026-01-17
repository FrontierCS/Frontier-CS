#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// The box size
const int W = 100000;

// Function to perform a query
// Outputs the coordinates of the line segment endpoints
// Returns the length of the intersection with the disk
double query(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    cin >> res;
    return res;
}

// Function to output the final answer
void answer(int x, int y, int r) {
    cout << "answer " << x << " " << y << " " << r << endl;
}

int main() {
    // 1. Scan for any vertical line intersecting the disk
    // We scan x = 0, 199, 398... 
    // The disk diameter is at least 200, so the intersection interval on x-axis is at least 199 integers long.
    // A step of 199 guarantees we hit the interval.
    int step_x = 199;
    int x_hit = -1;
    
    for (int x = 0; x <= W; x += step_x) {
        double l = query(x, 0, x, W);
        if (l > 1e-8) {
            x_hit = x;
            break;
        }
    }
    
    // 2. Binary search for the left boundary x_L of the vertical intersection range
    // We search in [0, x_hit]. The property "intersects" is monotonic (0...0 1...1).
    int low = 0, high = x_hit;
    int x_L = x_hit;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        double l = query(mid, 0, mid, W);
        if (l > 1e-8) {
            x_L = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // 3. Binary search for the right boundary x_R
    // We search in [x_hit, W].
    low = x_hit; high = W;
    int x_R = x_hit;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        double l = query(mid, 0, mid, W);
        if (l > 1e-8) {
            x_R = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    // Determine X center and Radius R
    // The range of integers with intersection is [x_L, x_R]
    // Center X is midpoint. Width is 2*R (roughly), specifically x_R - x_L = 2*R - 2.
    int X = (x_L + x_R) / 2;
    int R = (x_R - x_L) / 2 + 1;

    // 4. Scan for a diagonal line intersecting the disk to find Y
    // We use lines y = x + k. k is the parameter.
    // The disk projection on the normal direction has width 2*R.
    // In terms of k, the interval of intersection has width 2*sqrt(2)*R approx 2.828*R.
    // We use a safe step size of 2.5*R.
    int step_k = (int)(2.5 * R);
    if (step_k < 1) step_k = 1;

    // k ranges roughly from -X to W-X.
    int min_k = -X;
    int max_k = W - X;
    
    double l_hit = 0;
    int k_hit = -2000000;

    for (int k = min_k; k <= max_k; k += step_k) {
        int x1, y1, x2, y2;
        if (k >= 0) {
            x1 = 0; y1 = k;
            x2 = W - k; y2 = W;
        } else {
            x1 = -k; y1 = 0;
            x2 = W; y2 = W + k;
        }
        
        if (x1 < 0 || x1 > W || y1 < 0 || y1 > W || x2 < 0 || x2 > W || y2 < 0 || y2 > W) continue;

        double l = query(x1, y1, x2, y2);
        if (l > 1e-8) {
            l_hit = l;
            k_hit = k;
            break;
        }
    }

    // 5. Refine measurement if the hit was too close to the center
    // If l_hit is large (close to 2R), the line is near the center, making distance calculation sensitive to errors.
    // We shift k by R to get a chord further from center.
    if (l_hit > 1.5 * R) {
        int shift = R;
        int k_new = k_hit + shift;
        bool checked_new = false;

        // Try shifting positive
        int x1, y1, x2, y2;
        if (k_new <= max_k + W) { // Loose bound check
            if (k_new >= 0) {
                x1 = 0; y1 = k_new;
                x2 = W - k_new; y2 = W;
            } else {
                x1 = -k_new; y1 = 0;
                x2 = W; y2 = W + k_new;
            }
            if (x1 >= 0 && x1 <= W && y1 >= 0 && y1 <= W && x2 >= 0 && x2 <= W && y2 >= 0 && y2 <= W) {
                double l_new = query(x1, y1, x2, y2);
                if (l_new > 1e-8) {
                    l_hit = l_new;
                    k_hit = k_new;
                    checked_new = true;
                }
            }
        }
        
        // If positive shift didn't work well (e.g. out of bounds), try negative
        if (!checked_new) {
            k_new = k_hit - shift;
            if (k_new >= min_k - W) {
                if (k_new >= 0) {
                    x1 = 0; y1 = k_new;
                    x2 = W - k_new; y2 = W;
                } else {
                    x1 = -k_new; y1 = 0;
                    x2 = W; y2 = W + k_new;
                }
                if (x1 >= 0 && x1 <= W && y1 >= 0 && y1 <= W && x2 >= 0 && x2 <= W && y2 >= 0 && y2 <= W) {
                    double l_new = query(x1, y1, x2, y2);
                    if (l_new > 1e-8) {
                        l_hit = l_new;
                        k_hit = k_new;
                    }
                }
            }
        }
    }

    // 6. Calculate Y
    // d is the distance from the center (X, Y) to the line x - y + k = 0
    // d = |X - Y + k| / sqrt(2)
    // Also chord length l = 2 * sqrt(R^2 - d^2) => d = sqrt(R^2 - (l/2)^2)
    double d = sqrt(max(0.0, (double)R*R - (l_hit/2.0)*(l_hit/2.0)));
    
    // |X - Y + k| = d * sqrt(2)
    // Y = X + k +/- d * sqrt(2)
    int Y1 = (int)round(X + k_hit - d * sqrt(2.0));
    int Y2 = (int)round(X + k_hit + d * sqrt(2.0));
    
    int Y_final = -1;
    
    // Filter by validity (disk must be inside box)
    bool v1 = (Y1 >= R && Y1 <= W - R);
    bool v2 = (Y2 >= R && Y2 <= W - R);
    
    if (v1 && !v2) {
        Y_final = Y1;
    } else if (!v1 && v2) {
        Y_final = Y2;
    } else {
        // Disambiguate if both are valid
        // Query horizontal line through Y1. If Y1 is center, length should be 2R.
        double check = query(0, Y1, W, Y1);
        if (abs(check - 2.0 * R) < 2.0) { // Allow some tolerance
            Y_final = Y1;
        } else {
            Y_final = Y2;
        }
    }
    
    answer(X, Y_final, R);

    return 0;
}