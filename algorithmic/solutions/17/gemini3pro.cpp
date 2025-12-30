#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Cache for query results to avoid asking the same query twice
map<pair<int, int>, int> cache_query;

int ask(int l, int r) {
    if (l >= r) return -1;
    if (cache_query.count({l, r})) {
        return cache_query[{l, r}];
    }
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return cache_query[{l, r}] = res;
}

void solve() {
    int n;
    cin >> n;
    
    cache_query.clear();
    
    // Find the position of the second largest element in [1, n].
    int idx = ask(1, n);
    
    // Determine which side the largest element (n) is on relative to idx.
    // If idx is the second largest in [1, n], then n is the largest.
    // If n is in [1, idx], then the second largest in [1, idx] must be idx.
    // If n is in [idx, n], then the second largest in [idx, n] must be idx.
    
    bool left_side = false;
    
    if (idx == 1) {
        left_side = false;
    } else if (idx == n) {
        left_side = true;
    } else {
        // Query [1, idx] to check if n is on the left
        int check = ask(1, idx);
        if (check == idx) {
            // n is in [1, idx]. Since n != P[idx], n is in [1, idx-1]
            left_side = true;
        } else {
            // n is in [idx+1, n]
            left_side = false;
        }
    }
    
    if (left_side) {
        // Binary search in [1, idx-1]
        // We look for the largest index p such that ask(p, idx) == idx.
        // If ask(mid, idx) == idx, it means n is in [mid, idx].
        // Since we know n is in [1, idx-1], this means n >= mid.
        int l = 1, r = idx - 1;
        int ans = 1; 
        
        while (l <= r) {
            int mid = (l + r + 1) / 2;
            if (ask(mid, idx) == idx) {
                ans = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        cout << "! " << ans << endl;
    } else {
        // Binary search in [idx+1, n]
        // We look for the smallest index p such that ask(idx, p) == idx.
        // If ask(idx, mid) == idx, it means n is in [idx, mid].
        // Since we know n is in [idx+1, n], this means n <= mid.
        int l = idx + 1, r = n;
        int ans = n;
        
        while (l <= r) {
            int mid = (l + r) / 2;
            if (ask(idx, mid) == idx) {
                ans = mid;
                r = mid - 1;
            } else {
                l = mid + 1;
            }
        }
        cout << "! " << ans << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    // cin.tie(NULL); // Do not untie in interactive problems if you rely on cin flushing cout, 
                      // but usually with endl it's fine. 
                      // Safest to just not sync and use endl.
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}