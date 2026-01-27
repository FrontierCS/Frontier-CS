#include <iostream>
#include <vector>

using namespace std;

// Global variables to store the array and its size
int n;
vector<int> a;

// Recursive function to solve the problem for range [l, r]
void solve(int l, int r) {
    if (l > r) return;

    // Pruning: skip indices that are already filled.
    // This is crucial for performance and to ensure we don't overwrite correctly filled values unnecessarily.
    while (l <= r && a[l] != 0) l++;
    while (r >= l && a[r] != 0) r--;
    
    if (l > r) return;

    // Perform the query for the current range
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    
    // If the response is invalid, terminate (as per protocol)
    if (x == -1) exit(0);

    // If the frequency matches the range length, the whole range is filled with x
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) a[i] = x;
        return;
    }

    int mid = (l + r) / 2;
    
    // Recursively solve the left half
    solve(l, mid);
    
    // After returning from the left half, a[l...mid] is partially or fully filled.
    // We can use the information from the query (x, f) to fill some values in the right half.
    // Specifically, if the block of 'x' crosses the midpoint 'mid', we can determine how many 'x's 
    // fall into the right half and fill them immediately.
    
    // Check if the element at mid is x. Since the array is sorted, if a[mid] == x, 
    // then the occurrences of x in [l, mid] are contiguous ending at mid.
    if (a[mid] == x) {
        int c = 0;
        int ptr = mid;
        // Count how many times x appears in a[l...mid].
        // Since f is the frequency in [l, r], we only count occurrences within [l, mid].
        // The condition ptr >= l ensures we stay within the query bounds.
        while (ptr >= l && a[ptr] == x) {
            c++;
            ptr--;
        }
        
        // The remaining occurrences must be in the right half, starting immediately after mid.
        int rem = f - c;
        for (int i = 1; i <= rem; ++i) {
            // Ensure we don't go out of bounds, though logic dictates mid + i <= r
            if (mid + i <= n) a[mid + i] = x;
        }
    }
    
    // Recursively solve the right half
    solve(mid + 1, r);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (cin >> n) {
        a.resize(n + 1, 0); // 1-based indexing
        solve(1, n);
        
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << a[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }
    return 0;
}