#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to perform the query
// Returns the index of the second largest number in the range [l, r]
int query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;

    // Find the position of the second largest element in the full range [1, n].
    // Let this position be s.
    // The largest element (target) is either in [1, s-1] or [s+1, n].
    int s = query(1, n);

    bool go_left = false;
    
    // Determine which side of s the largest element (n) is on.
    if (s == n) {
        // If the second largest is at index n, the largest must be to the left.
        go_left = true;
    } else if (s == 1) {
        // If the second largest is at index 1, the largest must be to the right.
        go_left = false;
    } else {
        // s is strictly inside (1, n). We need to determine the direction.
        // We query the range [1, s].
        // If the second largest in [1, s] is s, it means both the second largest (global)
        // and the largest (global) are in [1, s]. Thus n is in [1, s].
        // Otherwise, n is not in [1, s], so it must be in [s+1, n].
        int check = query(1, s);
        if (check == s) {
            go_left = true;
        } else {
            go_left = false;
        }
    }

    if (go_left) {
        // We know n is in [1, s-1].
        // We also know that for the range [1, s], the second max is at s.
        // Property: For any sub-segment [l, s], if it contains n, the second max will be s.
        // If it does not contain n, the max will be P[s] (since P[s] is global 2nd max),
        // so the query result will NOT be s.
        // We want to find the largest l in [1, s-1] such that query(l, s) == s.
        // This l will be the position of n.
        
        int low = 1, high = s - 1;
        int ans = 1; // Default, though loop should find correct answer

        while (low <= high) {
            int mid = (low + high) / 2;
            
            // Optimization: If mid is 1, we know query(1, s) is s from previous logic.
            // This saves a query.
            if (mid == 1) {
                ans = max(ans, 1);
                low = mid + 1;
                continue;
            }

            int res = query(mid, s);
            if (res == s) {
                // n is in [mid, s], try to shorten range from left (find larger l)
                ans = mid;
                low = mid + 1;
            } else {
                // n is not in [mid, s], so n must be in [1, mid-1]
                high = mid - 1;
            }
        }
        cout << "! " << ans << endl;

    } else {
        // We know n is in [s+1, n].
        // Property: For any sub-segment [s, r], if it contains n, the second max will be s.
        // If it does not contain n (i.e., r < pos[n]), P[s] is max, so query != s.
        // We want to find the smallest r in [s+1, n] such that query(s, r) == s.
        // This r will be the position of n.
        
        int low = s + 1, high = n;
        int ans = n;

        while (low <= high) {
            int mid = (low + high) / 2;

            // Optimization: If mid is n, we know query(s, n) is s.
            // This relies on s being 2nd max global and n being max global.
            if (mid == n) {
                ans = min(ans, n);
                high = mid - 1;
                continue;
            }

            int res = query(s, mid);
            if (res == s) {
                // n is in [s, mid], try to shorten range from right (find smaller r)
                ans = mid;
                high = mid - 1;
            } else {
                // n is not in [s, mid], so n must be in [mid+1, n]
                low = mid + 1;
            }
        }
        cout << "! " << ans << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    // cin.tie(NULL); // Optional for interactive problems
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}