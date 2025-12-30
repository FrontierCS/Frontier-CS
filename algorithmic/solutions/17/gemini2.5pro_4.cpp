#include <iostream>

// Function to perform a query. It prints the query to stdout, ensures the
// output is flushed, and reads the interactor's response from stdin.
int query(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int pos;
    std::cin >> pos;
    return pos;
}

// Main logic to solve a single test case
void solve() {
    int n;
    std::cin >> n;

    // Initial query to find the position of n-1, which serves as our first pivot.
    int s = query(1, n);

    int l, r, pivot;

    // Determine if n is to the left or right of s.
    if (s > 1) {
        int s_prime = query(1, s);
        if (s_prime == s) {
            // n is in [1, s-1]. p[s] is an upper bound for elements in this range.
            l = 1;
            r = s - 1;
            pivot = s;
        } else {
            // n is in [s+1, n].
            l = s + 1;
            r = n;
            pivot = s;
        }
    } else { // s == 1, so n must be to the right.
        l = 2;
        r = n;
        pivot = 1;
    }
    
    // Iteratively narrow down the range [l, r] containing n.
    while (l < r) {
        int m;
        // Find the position of the maximum element in p[l...r].
        // We query a range including [l, r] and the pivot. p[pivot] is the max
        // in this query range, so the second max is the max of p[l...r].
        if (pivot < l) {
            m = query(pivot, r);
        } else { // pivot > r
            m = query(l, pivot);
        }

        // m is now the position of the max element in p[l...r] and our new pivot.
        // Handle edge cases where m is a boundary of the current range.
        if (m == l) {
            l = m + 1;
            pivot = m;
            continue;
        }
        if (m == r) {
            r = m - 1;
            pivot = m;
            continue;
        }

        // Determine if n is to the left or right of m.
        // We choose the smaller sub-range to query to optimize total query length.
        if (m - l <= r - m) { // Left part is smaller or equal
            int s_prime = query(l, m);
            if (s_prime == m) {
                // n is in [l, m-1]
                r = m - 1;
            } else {
                // n is in [m+1, r]
                l = m + 1;
            }
        } else { // Right part is smaller
            int s_prime = query(m, r);
            if (s_prime == m) {
                // n is in [m+1, r]
                l = m + 1;
            } else {
                // n is in [l, m-1]
                r = m - 1;
            }
        }
        pivot = m;
    }

    // When l == r, we have found the position of n.
    std::cout << "! " << l << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}