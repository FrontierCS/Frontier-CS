#include <iostream>
#include <vector>

using namespace std;

// Global array to store the result
int n;
vector<int> a;

/**
 * Perform a query for the subarray a[l...r].
 * Returns a pair {mode, frequency}.
 */
pair<int, int> query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    return {x, f};
}

/**
 * Recursive function to restore the array in range [l, r].
 * Returns {mode, frequency} of the current range [l, r].
 */
pair<int, int> solve(int l, int r) {
    // Query the current range
    pair<int, int> res = query(l, r);
    int m = res.first;
    int f = res.second;
    int len = r - l + 1;

    // Base Case: If frequency equals length, the whole range is composed of 'm'.
    if (f == len) {
        for (int i = l; i <= r; ++i) {
            a[i] = m;
        }
        return res;
    }

    int mid = l + (r - l) / 2;

    // Solve for the left half
    pair<int, int> left_res = solve(l, mid);
    int fL = left_res.second;

    // Optimization Step:
    // We know there are 'f' occurrences of 'm' in total in [l, r].
    // The number of occurrences of 'm' in the left half [l, mid] is at most 'fL'.
    // (It is exactly 'fL' if left_res.first == m, and strictly less or irrelevant otherwise).
    // Therefore, the number of 'm's in the right half must be at least f - fL.
    // If this lower bound equals the length of the right half, then the right half
    // is fully composed of 'm'.
    
    int right_len = r - mid;
    int m_in_right_lower_bound = f - fL;

    if (m_in_right_lower_bound == right_len) {
        // Right half is all 'm's
        for (int i = mid + 1; i <= r; ++i) {
            a[i] = m;
        }
    } else {
        // Otherwise, we must solve the right half recursively
        solve(mid + 1, r);
    }

    return res;
}

int main() {
    // Optimize I/O; interactive problems require careful flushing.
    // 'endl' forces a flush, so we can disable sync/tie for standard streams safely.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> n) {
        a.resize(n + 1);
        
        // Start the recursive solution
        solve(1, n);

        // Output the result
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << a[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }
    
    return 0;
}