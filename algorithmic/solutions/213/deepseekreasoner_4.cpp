#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    // Choose x as sqrt(n) to balance block moves and fine adjustments
    int x = max(2, (int)sqrt(n));

    // Store operations: ((l, r), direction) where direction 0 = left, 1 = right
    vector<pair<pair<int, int>, int>> ops;

    // Helper functions to apply a shift and update the array
    auto left_shift = [&](int l, int r) {
        int t = a[l];
        for (int i = l; i < r; ++i) a[i] = a[i + 1];
        a[r] = t;
    };
    auto right_shift = [&](int l, int r) {
        int t = a[r];
        for (int i = r; i > l; --i) a[i] = a[i - 1];
        a[l] = t;
    };

    // Process each target position from left to right
    for (int i = 1; i <= n; ++i) {
        // Find current position of number i
        int p = -1;
        for (int j = i; j <= n; ++j) {
            if (a[j] == i) {
                p = j;
                break;
            }
        }
        if (p == i) continue;

        // Phase 1: large jumps using segments of length x
        while (p - i >= x - 1) {
            int l = p - x + 1;
            if (l >= i) {  // segment stays within unsorted part
                ops.push_back({{l, p}, 1});  // right shift
                right_shift(l, p);
                p = l;
            } else {
                break;
            }
        }

        // Phase 2: fine adjustment using a segment starting at i
        if (p != i) {
            // Ensure the segment [i, i+x-1] is within array bounds
            if (i + x - 1 <= n) {
                int d = p - i;
                for (int k = 0; k < d; ++k) {
                    ops.push_back({{i, i + x - 1}, 0});  // left shift
                    left_shift(i, i + x - 1);
                }
            } else {
                // For the last few elements, use a fallback:
                // move left one step at a time using the largest possible segment
                while (p > i) {
                    // Choose a segment that contains p and p-1, has length x, and lies inside [i, n]
                    int l = max(i, p - x + 1);
                    int r = l + x - 1;
                    if (r > n) {
                        l = n - x + 1;
                        r = n;
                    }
                    // If the segment is valid and contains both p-1 and p, do a left shift
                    if (l <= p - 1 && r >= p) {
                        ops.push_back({{l, r}, 0});
                        left_shift(l, r);
                        --p;
                    } else {
                        // Should not happen with reasonable x; break to avoid infinite loop
                        break;
                    }
                }
            }
        }
    }

    // Output the chosen x and the sequence of operations
    cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.first.first << " " << op.first.second << " " << op.second << "\n";
    }

    return 0;
}