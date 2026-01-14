#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.length();

    // Store indices of '1's. 
    // Add sentinels -1 and n to handle boundaries easily.
    // 'pos' will contain {-1, index_of_1st_1, index_of_2nd_1, ..., n}
    vector<int> pos;
    pos.reserve(n + 2);
    pos.push_back(-1);
    for (int i = 0; i < n; i++) {
        if (s[i] == '1') {
            pos.push_back(i);
        }
    }
    pos.push_back(n);

    int m = (int)pos.size() - 2; // actual number of 1s in the string
    long long ans = 0;

    // Iterate over the number of '1's (k) in the substring.
    // We want substrings where count('0') == k^2.
    // Since length = count('0') + count('1') = k^2 + k, 
    // we only need to check k such that k^2 + k <= n.
    // This implies k is roughly up to sqrt(n).
    
    for (int k = 1; k <= m; k++) {
        // If the minimum length for k ones exceeds n, we can stop.
        if ((long long)k * k + k > n) break;

        long long k2 = (long long)k * k;

        // Iterate over all valid windows of k ones in the 'pos' array.
        // The ones in the current window are at indices pos[i], pos[i+1], ..., pos[i+k-1].
        // This corresponds to the i-th '1' up to the (i+k-1)-th '1'.
        // The bounds for expanding this substring are strictly between pos[i-1] and pos[i+k].
        
        for (int i = 1; i <= m - k + 1; i++) {
            // Optimization: Pruning invalid windows early.
            // The maximum range of the substring is (pos[i-1], pos[i+k]).
            // The length of this range is pos[i+k] - pos[i-1] - 1.
            // This range contains exactly k ones.
            // So the maximum number of zeros available is (pos[i+k] - pos[i-1] - 1) - k.
            // If this is less than the required k^2 zeros, we can skip this window.
            // This check is crucial for performance when '1's are dense.
            if ((pos[i + k] - pos[i - 1] - 1 - k) < k2) continue;

            int u = pos[i];            // Index of the first '1' in the substring
            int v = pos[i + k - 1];    // Index of the last '1' in the substring

            // Number of zeros strictly inside the core range [u, v]
            // Length of [u, v] is v - u + 1. It contains k ones.
            int z_in = (v - u + 1) - k;
            
            // We need 'target' more zeros from the left and right extensions combined.
            long long target = k2 - z_in;
            
            // If z_in > k^2, it's impossible (already too many zeros between the first and last 1)
            if (target < 0) continue;

            // Available zeros on left (between pos[i-1] and u)
            int l_avail = u - pos[i - 1] - 1;
            // Available zeros on right (between v and pos[i+k])
            int r_avail = pos[i + k] - v - 1;

            // We need to count pairs (x, y) such that x + y = target,
            // with 0 <= x <= l_avail and 0 <= y <= r_avail.
            // Solving for x: y = target - x.
            // 0 <= target - x <= r_avail  =>  target - r_avail <= x <= target.
            // Also 0 <= x <= l_avail.
            // So, x must be in [max(0, target - r_avail), min(l_avail, target)].
            
            long long min_x = target - r_avail;
            if (min_x < 0) min_x = 0;
            
            long long max_x = l_avail;
            if (max_x > target) max_x = target;
            
            if (max_x >= min_x) {
                ans += (max_x - min_x + 1);
            }
        }
    }

    cout << ans << endl;

    return 0;
}