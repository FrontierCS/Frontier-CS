#include <iostream>
#include <vector>
#include <map>
#include <cstdlib>

using namespace std;

// Maximum value of N as per problem statement
const int MAXN = 200005;

// Array to store the result
int a[MAXN];
// Map to store a known position of each distinct element found so far
map<int, int> pos;

/**
 * Recursive function to solve the problem for the range [l, r].
 * Uses a divide and conquer strategy with pruning based on known sorted array properties.
 */
void solve(int l, int r) {
    // Trim indices from the left that are already filled
    while (l <= r && a[l] != 0) l++;
    // Trim indices from the right that are already filled
    while (r >= l && a[r] != 0) r--;
    
    // Base case: if range is empty or invalid
    if (l > r) return;

    // Interactive query
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    
    if (x == -1) exit(0); // Should not happen with correct logic

    // Optimization: If the frequency of x equals the length of the current range,
    // then the entire range [l, r] is filled with x.
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) a[i] = x;
        pos[x] = l; // Record that we found x at position l
        return;
    }

    // Anchor Optimization:
    // If we have previously encountered the value x, we know its position 'p' (stored in pos[x]).
    // Since the array is sorted, all occurrences of x must be contiguous.
    // Because x is present in the current unfilled range [l, r] (implied by the query result),
    // the block of x must connect to the previously found position 'p'.
    // 'p' cannot be inside [l, r] because [l, r] consists of unfilled (0) elements,
    // and pos[x] is set only when we fill elements.
    if (pos.count(x)) {
        int p = pos[x];
        
        if (p < l) {
            // x is anchored to the left of the current range.
            // Since x is contiguous and present in [l, r], it must start at l.
            // It occupies the first f positions of [l, r].
            for (int i = 0; i < f; ++i) a[l + i] = x;
            pos[x] = l; // Update anchor (optional)
            // Recurse on the remaining part of the range
            solve(l + f, r);
            return;
        } else if (p > r) {
            // x is anchored to the right of the current range.
            // It must occupy the last f positions of [l, r].
            for (int i = 0; i < f; ++i) a[r - i] = x;
            pos[x] = r;
            // Recurse on the remaining part
            solve(l, r - f);
            return;
        }
    }

    // If no optimizations apply, split the range and recurse.
    int mid = (l + r) / 2;
    solve(l, mid);
    solve(mid + 1, r);
}

int main() {
    // Optimize standard I/O operations (though flushing is necessary for interactive problems)
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Solve for the entire array
    solve(1, n);

    // Output the result
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << a[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}