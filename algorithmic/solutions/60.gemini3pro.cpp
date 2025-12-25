#include <iostream>
#include <cmath>
#include <algorithm>
#include <vector>
#include <iomanip>

using namespace std;

// Function to query the system
// Coordinates are integers between 0 and 100000
double query(long long x1, long long y1, long long x2, long long y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double ret;
    cin >> ret;
    return ret;
}

int main() {
    // The problem requires flushing stdout, which endl does automatically.
    // We will find the center (Cx, Cy) and radius R.
    
    long long x_hit = -1;
    double l_x = 0;
    
    // 1. Scan vertical lines to find X-coordinate intersection
    // The disk radius R >= 100, so diameter >= 200.
    // Scanning with step 199 guarantees hitting the disk.
    // Max queries ~ 503
    for (long long x = 0; x <= 100000; x += 199) {
        double l = query(x, 0, x, 100000);
        if (l > 0) {
            x_hit = x;
            l_x = l;
            break;
        }
    }
    
    // 2. Refine X to find Center X (Cx) and Radius (R)
    // We need two distinct vertical chords to determine Cx and R.
    long long x2 = -1;
    double l_x2 = 0;
    
    // Try the right neighbor
    if (x_hit + 1 <= 100000) {
        double l = query(x_hit + 1, 0, x_hit + 1, 100000);
        if (l > 0) {
            x2 = x_hit + 1;
            l_x2 = l;
        }
    }
    
    // If right neighbor didn't hit (boundary) or out of bounds, try left neighbor
    if (x2 == -1) {
        x2 = x_hit - 1;
        // x2 should be >= 0 because if x_hit=0, then x_hit+1=1 must have worked.
        l_x2 = query(x2, 0, x2, 100000);
    }
    
    // Calculate Cx
    // Using formula derived from: (k - Cx)^2 + (L/2)^2 = R^2
    // Subtracting two instances: (k1-Cx)^2 + (L1/2)^2 = (k2-Cx)^2 + (L2/2)^2
    // Solves to: Cx = (k1+k2)/2 - (L2^2 - L1^2)/(8*(k1-k2))
    double num = l_x2 * l_x2 - l_x * l_x;
    double den = 8.0 * (double)(x2 - x_hit);
    double cx_val = (double)(x_hit + x2) / 2.0 - num / den;
    long long Cx = round(cx_val);
    
    // Calculate R
    // R^2 = (k - Cx)^2 + (L/2)^2
    double r2_val = pow((double)(x_hit - Cx), 2) + pow(l_x / 2.0, 2);
    long long R = round(sqrt(r2_val));
    
    // 3. Scan horizontal lines to find Y-coordinate intersection
    long long y_hit = -1;
    double l_y = 0;
    
    for (long long y = 0; y <= 100000; y += 199) {
        double l = query(0, y, 100000, y);
        if (l > 0) {
            y_hit = y;
            l_y = l;
            break;
        }
    }
    
    // 4. Calculate candidates for Cy
    // The chord length at y_hit determines the vertical distance to center |y_hit - Cy|.
    // |y_hit - Cy| = sqrt(R^2 - (L/2)^2)
    double dy_sq = (double)R*R - pow(l_y / 2.0, 2);
    if (dy_sq < 0) dy_sq = 0;
    double dy = sqrt(dy_sq);
    
    long long Cy1 = round(y_hit - dy);
    long long Cy2 = round(y_hit + dy);
    
    long long Cy = Cy1;
    
    if (Cy1 != Cy2) {
        // Disambiguate between Cy1 and Cy2
        // We choose a test Y that yields significantly different chord lengths for Cy1 vs Cy2.
        
        // We avoid probing exactly symmetrically between them or at points where distances match.
        // A simple offset from one candidate works well, provided it's not symmetric.
        double current_dy = abs((double)(y_hit - Cy1));
        double offset = 0.5 * R;
        // Avoid symmetry case where offset approx equals current_dy (i.e. probing near y_hit)
        if (abs(current_dy - offset) < 0.1 * R) {
            offset = 0.3 * R;
        }
        
        long long test_y = round(Cy1 + offset);
        
        // Ensure test_y is within bounds [0, 100000]
        if (test_y > 100000) {
            test_y = round(Cy1 - offset);
        } else if (test_y < 0) {
            test_y = round(Cy1 + offset);
        }
        
        // Clamp to be safe
        if (test_y > 100000) test_y = 100000;
        if (test_y < 0) test_y = 0;

        double check_l = query(0, test_y, 100000, test_y);
        
        // Calculate expected lengths
        double d1 = abs((double)test_y - Cy1);
        double exp1 = (d1 >= R) ? 0.0 : 2.0 * sqrt((double)R*R - d1*d1);
        
        double d2 = abs((double)test_y - Cy2);
        double exp2 = (d2 >= R) ? 0.0 : 2.0 * sqrt((double)R*R - d2*d2);
        
        if (abs(check_l - exp1) < abs(check_l - exp2)) {
            Cy = Cy1;
        } else {
            Cy = Cy2;
        }
    }
    
    cout << "answer " << Cx << " " << Cy << " " << R << endl;
    
    return 0;
}