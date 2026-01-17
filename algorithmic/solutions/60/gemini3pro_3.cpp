#include <iostream>
#include <cmath>
#include <algorithm>
#include <vector>

using namespace std;

// Function to send query and receive response
double query(long long x1, long long y1, long long x2, long long y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double res;
    cin >> res;
    return res;
}

int main() {
    // Problem constraints
    const long long L = 100000;
    
    // --- Step 1: Find X and R ---
    // We scan vertical lines x = k.
    // The disk radius R >= 100. The non-zero interval for x is (X-R, X+R), length 2R >= 200.
    // Scanning with step 199 ensures we hit at least one vertical line intersecting the disk.
    
    long long x_hit = -1;
    double len_hit = 0.0;
    
    for (long long x = 100; x <= L; x += 199) {
        double res = query(x, 0, x, L);
        if (res > 1e-7) {
            x_hit = x;
            len_hit = res;
            break;
        }
    }
    
    // We need two points to determine circle parameters. 
    // Try the right neighbor of the hit.
    long long x_a = x_hit;
    double len_a = len_hit;
    long long x_b = x_hit + 1;
    double len_b = 0.0;
    
    // Check bounds for neighbor query
    if (x_b <= L) {
        len_b = query(x_b, 0, x_b, L);
    }
    
    // If the right neighbor is outside the disk (len ~ 0), try the left neighbor.
    // One neighbor must be inside since diameter >= 200.
    if (len_b < 1e-7) {
        x_b = x_hit - 1;
        len_b = query(x_b, 0, x_b, L);
    }
    
    // Calculate X and R.
    // Intersection length L at distance d from center: (L/2)^2 + d^2 = R^2
    // Let v = (len/2)^2. v = R^2 - (X - x)^2
    double va = (len_a / 2.0) * (len_a / 2.0);
    double vb = (len_b / 2.0) * (len_b / 2.0);
    
    // va + (X - xa)^2 = vb + (X - xb)^2
    // va - vb = (X - xb)^2 - (X - xa)^2 = (xa - xb)(2X - xa - xb)
    // 2X = xa + xb + (va - vb)/(xa - xb)
    double X_calc = (x_a + x_b + (va - vb) / (double)(x_a - x_b)) / 2.0;
    long long X = (long long)round(X_calc);
    
    double R_calc = sqrt(max(0.0, va + (X - x_a) * (X - x_a)));
    long long R = (long long)round(R_calc);
    
    // --- Step 2: Find Y ---
    // Now we know R. We scan horizontal lines y = k.
    // We can use a larger step size: 2R - 1.
    // This step size guarantees that any interval of length 2R (the disk span) is hit.
    
    long long y_hit = -1;
    double len_y_hit = 0.0;
    long long step_y = max(1LL, 2 * R - 1);
    
    // Start scanning from R because Y >= R.
    for (long long y = R; y <= L; y += step_y) {
        double res = query(0, y, L, y);
        if (res > 1e-7) {
            y_hit = y;
            len_y_hit = res;
            break;
        }
    }
    
    // Calculate distance of y_hit from center Y.
    // dy = |Y - y_hit|
    // dy^2 = R^2 - (len/2)^2
    double dy_calc = sqrt(max(0.0, (double)R * R - (len_y_hit / 2.0) * (len_y_hit / 2.0)));
    long long dy = (long long)round(dy_calc);
    
    long long Y1 = y_hit - dy;
    long long Y2 = y_hit + dy;
    long long Y = -1;
    
    bool y1_in = (Y1 >= R && Y1 <= L - R);
    bool y2_in = (Y2 >= R && Y2 <= L - R);
    
    if (y1_in && !y2_in) Y = Y1;
    else if (!y1_in && y2_in) Y = Y2;
    else {
        // Both in range.
        if (Y1 == Y2) Y = Y1;
        else {
            // Check which candidate is the center. The center gives the maximum chord length (2R).
            // Candidates are distinct, so one is center and other is reflection.
            // Reflection is strictly closer to edge or same distance? No, reflection is at distance 2*dy from center.
            // Center yields length 2R. Reflection yields < 2R.
            double res1 = query(0, Y1, L, Y1);
            double res2 = query(0, Y2, L, Y2);
            if (res1 > res2) Y = Y1;
            else Y = Y2;
        }
    }
    
    cout << "answer " << X << " " << Y << " " << R << endl;
    
    return 0;
}