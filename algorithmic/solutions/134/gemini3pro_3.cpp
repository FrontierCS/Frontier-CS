#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

// Structure to represent a rectangle in the 2D search space [1, n] x [1, n]
struct Rect {
    ll lx, rx, ly, ry;
    
    // Check if the rectangle is valid (non-empty)
    bool isValid() const {
        return lx <= rx && ly <= ry;
    }
    
    // Calculate area (using long double to prevent overflow with large coordinates)
    long double area() const {
        return (long double)(rx - lx + 1) * (long double)(ry - ly + 1);
    }
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ll n;
    if (!(cin >> n)) return 0;

    // Initially, the candidate region is the entire grid [1, n] x [1, n]
    vector<Rect> rects;
    rects.push_back({1, n, 1, n});

    int queries = 0;
    // We are allowed up to 10000 queries
    while (queries < 10000 && !rects.empty()) {
        // Greedy strategy: pick the rectangle with the largest area to bisect
        int bestIdx = -1;
        long double maxArea = -1.0;

        for (int i = 0; i < rects.size(); ++i) {
            long double a = rects[i].area();
            if (a > maxArea) {
                maxArea = a;
                bestIdx = i;
            }
        }

        if (bestIdx == -1) break; // Should not happen if rects is not empty

        // Query the midpoint of the chosen rectangle
        Rect current = rects[bestIdx];
        ll mx = current.lx + (current.rx - current.lx) / 2;
        ll my = current.ly + (current.ry - current.ly) / 2;

        cout << mx << " " << my << endl; // endl flushes the output
        queries++;

        int resp;
        cin >> resp;

        if (resp == 0) {
            // Found the secret numbers
            return 0;
        }

        vector<Rect> nextRects;
        // Optimization: reserve memory to avoid reallocations
        nextRects.reserve(rects.size() + 2);

        if (resp == 1) {
            // Response 1: x < a  =>  a >= mx + 1
            // We can clip all rectangles to have lx >= mx + 1
            ll newMinA = mx + 1;
            for (const auto& r : rects) {
                Rect nr = r;
                nr.lx = max(nr.lx, newMinA);
                if (nr.isValid()) {
                    nextRects.push_back(nr);
                }
            }
        } else if (resp == 2) {
            // Response 2: y < b  =>  b >= my + 1
            // We can clip all rectangles to have ly >= my + 1
            ll newMinB = my + 1;
            for (const auto& r : rects) {
                Rect nr = r;
                nr.ly = max(nr.ly, newMinB);
                if (nr.isValid()) {
                    nextRects.push_back(nr);
                }
            }
        } else if (resp == 3) {
            // Response 3: x > a OR y > b
            // This implies that the solution CANNOT be in the region [mx, n] x [my, n].
            // We subtract the region [mx, n] x [my, n] from all active rectangles.
            for (const auto& r : rects) {
                // Determine intersection of current rect 'r' and the removed region
                ll intLx = max(r.lx, mx);
                ll intLy = max(r.ly, my);
                
                // If there is an intersection
                if (intLx <= r.rx && intLy <= r.ry) {
                    // Split 'r' into up to two rectangles that cover r \setminus bad_region.
                    // The valid points are those in 'r' where (x < mx) OR (y < my).
                    
                    // Part 1: Region where x < mx
                    Rect r1 = r;
                    r1.rx = min(r1.rx, mx - 1);
                    if (r1.isValid()) {
                        nextRects.push_back(r1);
                    }
                    
                    // Part 2: Region where x >= mx AND y < my
                    // (Note: x >= mx part is max(r.lx, mx) to r.rx)
                    Rect r2 = r;
                    r2.lx = max(r2.lx, mx);
                    r2.ry = min(r2.ry, my - 1);
                    if (r2.isValid()) {
                        nextRects.push_back(r2);
                    }
                } else {
                    // No intersection with the bad region, keep the rectangle as is
                    nextRects.push_back(r);
                }
            }
        }
        
        rects = nextRects;
    }

    return 0;
}