#include <iostream>
#include <vector>

using namespace std;

// Global variables to store the array and its size
int n;
vector<int> a; // 1-indexed, stores values. 0 means unknown.

// Query range [l, r]
pair<int, int> ask_range(int l, int r) {
    if (l > r) return {-1, -1};
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    return {x, f};
}

// Query single element 'idx'
// Uses cache if available to avoid redundant queries
int get_val(int idx) {
    if (idx < 1 || idx > n) return -1; 
    if (a[idx] != 0) return a[idx];
    cout << "? " << idx << " " << idx << endl;
    int x, f; // f is always 1 for single element
    cin >> x >> f;
    a[idx] = x;
    return x;
}

// Recursive function to solve for range [l, r]
void solve(int l, int r) {
    if (l > r) return;

    // Optimization: if range ends are known and equal, the whole range is filled with that value.
    // This is valid because the array is sorted.
    if (a[l] != 0 && a[r] != 0 && a[l] == a[r]) {
        for (int i = l + 1; i < r; ++i) a[i] = a[l];
        return;
    }

    // Query the mode of the current range
    pair<int, int> res = ask_range(l, r);
    int x = res.first;
    int f = res.second;

    // If the frequency equals the range length, the whole range is x
    if (f == (r - l + 1)) {
        for (int i = l; i <= r; ++i) a[i] = x;
        return;
    }

    // Determine the range [L, L + f - 1] occupied by x
    int L = -1;

    // Optimization: Check boundaries first. This handles cases where we peel blocks from ends efficiently.
    // Check if x starts at l
    if (get_val(l) == x) {
        L = l;
    } else {
        // Check if x ends at r (meaning it starts at r - f + 1)
        if (get_val(r) == x) {
            L = r - f + 1;
        } else {
            // x is strictly inside [l, r].
            // We know a[l] < x and a[r] > x because the array is sorted and x is present.
            // We binary search for the first occurrence of x.
            // Valid start range is [l + 1, r - f].
            int low = l + 1;
            int high = r - f;
            int ans_idx = high; 

            while (low <= high) {
                int mid = low + (high - low) / 2;
                int val = get_val(mid);
                if (val == x) {
                    ans_idx = mid;
                    high = mid - 1; // look for earlier start
                } else if (val < x) {
                    low = mid + 1;
                } else { // val > x
                    high = mid - 1;
                }
            }
            L = ans_idx;
        }
    }

    // Fill the determined block of x
    for (int i = 0; i < f; ++i) {
        a[L + i] = x;
    }

    // Solve remaining subproblems. 
    // The filled block splits the problem into two independent subproblems.
    solve(l, L - 1);
    solve(L + f, r);
}

int main() {
    // Basic optimization for I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> n) {
        a.assign(n + 1, 0);
        solve(1, n);

        cout << "! ";
        for (int i = 1; i <= n; ++i) {
             cout << a[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }
    return 0;
}