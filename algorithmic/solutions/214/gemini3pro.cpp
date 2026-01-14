#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Use 1-based indexing for convenience
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }

    // We choose x = 3. This gives us reversal lengths of x-1 = 2 and x+1 = 4.
    // Length 2 reversal is an adjacent swap (distance 1 move).
    // Length 4 reversal reverses 4 elements (distance 3 move for the endpoints).
    // This combination allows us to move elements with step size 3 and 1,
    // achieving sorting in roughly N^2 / 12 operations, which fits within 200N.
    cout << 3 << "\n";

    vector<pair<int, int>> ops;
    
    // Helper lambda to record and perform reversal
    auto do_reverse = [&](int l, int r) {
        ops.push_back({l, r});
        reverse(a.begin() + l, a.begin() + r + 1);
    };

    // Bidirectional Selection Sort / Greedy approach
    // We maintain the unsorted range [L, R].
    // In each step, we move either the value L to position L or value R to position R.
    int L = 1, R = n;
    while (L < R) {
        int pL = -1, pR = -1;
        // Find current positions of values L and R
        for (int i = 1; i <= n; ++i) {
            if (a[i] == L) pL = i;
            if (a[i] == R) pR = i;
        }

        // Calculate distances to target positions
        int distL = pL - L;
        int distR = R - pR;

        // Choose the move that requires fewer operations (approx. distance / 3)
        if (distL <= distR) {
            // Move value L to the left end (L)
            int curr = pL;
            while (curr > L) {
                // Try to use the larger reversal (length 4) for a jump of 3
                if (curr - 3 >= L) {
                    // Reverse [curr-3, curr] moves element at curr to curr-3
                    do_reverse(curr - 3, curr);
                    curr -= 3;
                } else {
                    // Use the smaller reversal (length 2) for a jump of 1
                    do_reverse(curr - 1, curr);
                    curr -= 1;
                }
            }
            L++;
        } else {
            // Move value R to the right end (R)
            int curr = pR;
            while (curr < R) {
                // Try to use the larger reversal (length 4) for a jump of 3
                if (curr + 3 <= R) {
                    // Reverse [curr, curr+3] moves element at curr to curr+3
                    do_reverse(curr, curr + 3);
                    curr += 3;
                } else {
                    // Use the smaller reversal (length 2) for a jump of 1
                    do_reverse(curr, curr + 1);
                    curr += 1;
                }
            }
            R--;
        }
    }

    cout << ops.size() << "\n";
    for (auto& p : ops) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}