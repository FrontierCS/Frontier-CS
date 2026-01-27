#include <iostream>
#include <vector>

using namespace std;

// Array to store the reconstructed elements
const int MAXN = 200005;
int ans[MAXN];

// Recursive function to solve for range [l, r] using Divide & Conquer
// The logic relies on the fact that if a range has a mode with frequency
// equal to its length, then the range consists of identical elements (pure).
// Otherwise, we split the range. Since there are at most k distinct elements,
// the number of "pure" blocks is k. The number of queries will be proportional
// to k * log(n/k), which fits within limits for k=25000.
void solve(int l, int r) {
    if (l > r) return;

    // Interactive query
    cout << "? " << l << " " << r << endl;
    
    int x, f;
    cin >> x >> f;

    // Check for exit condition or invalid query response
    if (x == -1) exit(0);

    // If frequency equals the length of the subarray, the subarray is filled with x
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) {
            ans[i] = x;
        }
        return;
    }

    // Otherwise, the subarray contains mixed elements. Split and recurse.
    int mid = (l + r) / 2;
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (cin >> n) {
        // Start splitting from the full array
        solve(1, n);

        // Output the result
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << ans[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}