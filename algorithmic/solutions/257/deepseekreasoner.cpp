#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Array to store the restored sequence. Size covers max N (2*10^5).
int a[200005];

/**
 * Recursive function to solve for range [l, r].
 * Uses a divide and conquer approach similar to building a Segment Tree.
 * Queries the current range for mode and frequency.
 * If the range is "pure" (consists of only one value), fill it and return.
 * Otherwise, split into left and right sub-ranges.
 */
void solve(int l, int r) {
    if (l > r) return;

    // Perform query: "? l r"
    cout << "? " << l << " " << r << endl;
    
    // Read response: "x f"
    long long x_long;
    int f;
    // Input validation for robustness
    if (!(cin >> x_long >> f)) {
        exit(0);
    }
    
    // -1 indicates invalid query or error
    if (x_long == -1) {
        exit(0);
    }
    
    int x = (int)x_long;

    // If frequency equals the length of the range, all elements in [l, r] are equal to x.
    if (f == (r - l + 1)) {
        for (int i = l; i <= r; ++i) {
            a[i] = x;
        }
        return;
    }

    // Divide step: split the range into halves
    int mid = (l + r) / 2;
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    // Optimize I/O operations.
    // Note: interactive checking requires output flushing. 'endl' forces flush.
    // Untying cin from cout is safe here.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    // Read N
    if (cin >> n) {
        // Start the recursive solving process from the full array
        solve(1, n);

        // Output the final answer
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << a[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}