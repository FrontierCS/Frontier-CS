#include <iostream>

using namespace std;

// Function to interact with the judge
int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // Find the position of the second largest element in the entire array.
    // Let this position be s. Since n is the unique maximum, the second largest in [1, n]
    // is indeed the global second largest.
    int s = ask(1, n);
    
    bool search_left = false;
    
    // Determine which side of s the maximum n lies.
    if (s == 1) {
        // s is at index 1, so n must be in [2, n]
        search_left = false;
    } else if (s == n) {
        // s is at index n, so n must be in [1, n-1]
        search_left = true;
    } else {
        // s is in the middle. We need to check one side to determine where n is.
        // We choose the side with smaller length to minimize the sum of query lengths.
        // Left interval [1, s] has length s.
        // Right interval [s, n] has length n - s + 1.
        if (s < n - s + 1) {
            // Check left side [1, s]
            int res = ask(1, s);
            if (res == s) {
                // The second largest in [1, s] is at s.
                // This implies n is present in [1, s].
                search_left = true;
            } else {
                // n is not in [1, s], so it must be in [s+1, n].
                search_left = false;
            }
        } else {
            // Check right side [s, n]
            int res = ask(s, n);
            if (res == s) {
                // The second largest in [s, n] is at s.
                // This implies n is present in [s, n].
                search_left = false;
            } else {
                // n is not in [s, n], so it must be in [1, s-1].
                search_left = true;
            }
        }
    }
    
    int ans = -1;
    if (search_left) {
        // Binary search in [1, s-1] to find pos[n].
        // Property: query(k, s) returns s IF AND ONLY IF pos[n] is in [k, s].
        // Since pos[n] < s, this is equivalent to k <= pos[n].
        // We want to find the largest k such that query(k, s) == s.
        int l = 1, r = s - 1;
        while (l < r) {
            int mid = (l + r + 1) / 2;
            int res = ask(mid, s);
            if (res == s) {
                // pos[n] >= mid
                l = mid;
            } else {
                // pos[n] < mid
                r = mid - 1;
            }
        }
        ans = l;
    } else {
        // Binary search in [s+1, n] to find pos[n].
        // Property: query(s, k) returns s IF AND ONLY IF pos[n] is in [s, k].
        // Since pos[n] > s, this is equivalent to k >= pos[n].
        // We want to find the smallest k such that query(s, k) == s.
        int l = s + 1, r = n;
        while (l < r) {
            int mid = (l + r) / 2;
            int res = ask(s, mid);
            if (res == s) {
                // pos[n] <= mid
                r = mid;
            } else {
                // pos[n] > mid
                l = mid + 1;
            }
        }
        ans = l;
    }
    
    cout << "! " << ans << endl;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}