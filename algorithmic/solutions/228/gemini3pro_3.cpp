#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s;
    if (!(cin >> s)) return 0;
    
    int n = s.length();
    
    // p stores the indices of '1's in the string.
    // We add sentinels -1 and n to simplify gap calculations.
    vector<int> p;
    p.reserve(n + 2);
    p.push_back(-1);
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            p.push_back(i);
        }
    }
    p.push_back(n);
    
    int m = p.size() - 2; // The number of '1's in the string
    long long total_zeros = n - m; // The number of '0's in the string
    
    // g[j] stores the number of zeros between p[j] and p[j+1].
    // Indices of g range from 0 to m.
    // g[0] is the count of zeros before the first '1'.
    // g[i] (for 1 <= i < m) is the count of zeros between the i-th and (i+1)-th '1'.
    // g[m] is the count of zeros after the last '1'.
    vector<int> g;
    g.reserve(m + 1);
    for (size_t j = 0; j < p.size() - 1; ++j) {
        g.push_back(p[j+1] - p[j] - 1);
    }
    
    long long ans = 0;
    
    // Iterate over k, the number of '1's in the potential substring.
    // Since we need count('0') = count('1')^2, if k=0, count('0')=0, which implies an empty substring (or no 0s and 1s).
    // The problem asks for substrings, usually non-empty. An empty substring is trivial or not counted.
    // A substring with 0 ones and >0 zeros fails the condition (count0 != 0).
    // So we start k from 1.
    for (int k = 1; ; ++k) {
        long long k2 = 1LL * k * k;
        
        // Optimization:
        // If the required number of zeros (k^2) is greater than the total zeros available,
        // no substring with >= k ones can satisfy the condition.
        if (k2 > total_zeros) break;
        
        // If the minimum length of such a substring (k + k^2) exceeds n, stop.
        if (k2 + k > n) break;
        
        // current_z_in stores the sum of zeros strictly contained between the first and last '1' 
        // of the current block of k '1's.
        // For a block starting at the (i+1)-th '1' (index p[i+1]) and ending at the (i+k)-th '1' (index p[i+k]),
        // the inner gaps are g[i+1], g[i+2], ..., g[i+k-1].
        
        long long current_z_in = 0;
        // Initialize for i = 0 (block of 1s: p[1]...p[k])
        // Inner gaps are g[1]...g[k-1]
        for (int x = 1; x < k; ++x) {
            current_z_in += g[x];
        }
        
        // Iterate over all possible blocks of k ones.
        // i is the index in g such that g[i] is the gap immediately to the left of the block.
        // The block uses 1s at indices p[i+1] ... p[i+k].
        for (int i = 0; i <= m - k; ++i) {
            // We have a core substring from p[i+1] to p[i+k].
            // It contains k ones and current_z_in zeros.
            // We need a total of k^2 zeros.
            // We can extend to the left into g[i] and to the right into g[i+k].
            // Let u be zeros taken from left, v be zeros taken from right.
            // We require: u + v = k^2 - current_z_in
            // Constraints: 0 <= u <= g[i], 0 <= v <= g[i+k]
            
            long long target = k2 - current_z_in;
            
            if (target >= 0) {
                // From v <= g[i+k] and u + v = target => u >= target - g[i+k]
                // From v >= 0 => u <= target
                // Also 0 <= u <= g[i]
                
                long long lower = target - g[i+k];
                if (lower < 0) lower = 0;
                
                long long upper = target;
                if (upper > g[i]) upper = g[i];
                
                if (upper >= lower) {
                    ans += (upper - lower + 1);
                }
            }
            
            // Update current_z_in for the next window (slide right)
            // Remove the gap immediately after the start of the current block (g[i+1])
            // Add the gap immediately after the end of the current block (g[i+k])
            if (i < m - k) {
                current_z_in -= g[i+1];
                current_z_in += g[i+k];
            }
        }
    }
    
    cout << ans << endl;
    
    return 0;
}