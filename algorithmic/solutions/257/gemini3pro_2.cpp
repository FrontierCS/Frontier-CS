#include <iostream>
#include <vector>
#include <map>

using namespace std;

// Global variables to store the size and the answer
int n;
int ans[200005];

// Structure to store query results
struct QueryResult {
    int x, f;
};

// Memoization to avoid repeating identical queries
map<pair<int, int>, QueryResult> memo;

// Function to perform a query
QueryResult query(int l, int r) {
    if (l > r) return {-1, -1};
    // Check memoization
    if (memo.count({l, r})) return memo[{l, r}];
    
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    
    if (x == -1) exit(0); // Exit immediately on invalid query
    
    return memo[{l, r}] = {x, f};
}

// Recursive function to solve for range [l, r]
void solve(int l, int r) {
    if (l > r) return;
    
    // Get mode and frequency for current range
    QueryResult qr = query(l, r);
    int x = qr.x;
    int f = qr.f;
    
    // If the frequency matches the range length, fill the range with x
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) ans[i] = x;
        return;
    }
    
    // We know x appears f times in [l, r].
    // Since the array is sorted, these occurrences form a contiguous block: a[p ... p+f-1] = x.
    // We need to find the start index p. 
    // The possible range for p is [l, r - f + 1].
    
    int L = l, R = r - f + 1;
    int p = -1;
    
    // If there is only one possible position, we don't need to search
    if (L == R) {
        p = L;
    } else {
        // Binary search to find p
        while (L <= R) {
            int mid = L + (R - L) / 2;
            
            // Query a window of length f starting at mid
            // This window [mid, mid + f - 1] is guaranteed to be within [l, r]
            QueryResult q_sub = query(mid, mid + f - 1);
            
            if (q_sub.x < x) {
                // The mode of the window is smaller than x.
                // Since the array is sorted, this means we are to the left of x's block.
                L = mid + 1;
            } else if (q_sub.x > x) {
                // The mode of the window is larger than x.
                // This means we are to the right of x's block.
                R = mid - 1;
            } else {
                // q_sub.x == x. The window overlaps with x's block.
                if (q_sub.f == f) {
                    // The window is exactly x's block.
                    p = mid;
                    break;
                } else {
                    // Partial overlap. The intersection size is q_sub.f.
                    // The distance between mid and p is |mid - p| = f - q_sub.f.
                    int dist = f - q_sub.f;
                    
                    // Two candidates for p
                    int p1 = mid - dist;
                    int p2 = mid + dist;
                    
                    // We check p1. If p1 is valid and yields the correct block, then p = p1.
                    // Otherwise, p MUST be p2.
                    bool found = false;
                    if (p1 >= l && p1 <= r - f + 1) {
                         QueryResult q1 = query(p1, p1 + f - 1);
                         if (q1.x == x && q1.f == f) {
                             p = p1;
                             found = true;
                         }
                    }
                    
                    if (!found) {
                        p = p2;
                    }
                    break;
                }
            }
        }
    }
    
    // Fill the answer array for the identified block
    for (int i = 0; i < f; ++i) ans[p + i] = x;
    
    // Recurse on the left and right remaining parts
    solve(l, p - 1);
    solve(p + f, r);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (cin >> n) {
        solve(1, n);
        
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << ans[i] << (i == n ? "" : " ");
        }
        cout << endl;
    }
    
    return 0;
}