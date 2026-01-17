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

    int n = s.length();
    
    // Parse string to get counts of contiguous zeros
    // z stores the counts of consecutive '0's separated by '1's
    // If there are m '1's, there will be m+1 groups of '0's (some may be empty)
    // z[0] is zeros before first '1', z[1] between 1st and 2nd '1', ..., z[m] after last '1'
    vector<int> z;
    z.reserve(n + 1);
    
    int cur = 0;
    int m = 0; 
    for (char c : s) {
        if (c == '1') {
            z.push_back(cur);
            cur = 0;
            m++;
        } else {
            cur++;
        }
    }
    z.push_back(cur);

    // If there are no '1's, valid substring must have 0 ones and 0^2=0 zeros.
    // The only such substring is empty, but usually non-empty substrings are counted.
    // Assuming we only count non-empty substrings, the answer is 0.
    if (m == 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Precompute prefix sums of z to allow O(1) calculation of internal zeros
    // P[i] = z[0] + ... + z[i-1]
    vector<int> P(m + 2, 0);
    for (int i = 0; i < m + 1; ++i) {
        P[i+1] = P[i] + z[i];
    }

    long long ans = 0;
    int total_zeros = n - m;
    
    // Direct pointer access for speed in the inner loop
    const int* p_ptr = P.data();
    const int* z_ptr = z.data();

    // Iterate over the number of '1's (k) in the substring.
    // Constraints: 
    // 1. Need k^2 zeros, so k^2 <= total_zeros in the string.
    // 2. Need k ones, so k <= m.
    // Max value of k is approx sqrt(N), so this loop runs ~1414 times max.
    for (int k = 1; k <= m; ++k) {
        long long k2 = (long long)k * k;
        if (k2 > total_zeros) break; 

        int limit_i = m - k;
        
        // Sliding window over groups of ones
        // i represents the index of the group of ones starting after the i-th block of zeros (z[i])
        // The window involves k ones, bordered by z[i] on the left and z[i+k] on the right.
        for (int i = 0; i <= limit_i; ++i) {
            // Calculate sum of zeros strictly inside the block of k ones
            // These correspond to z[i+1] ... z[i+k-1]
            // Using prefix sums: P[i+k] - P[i+1]
            int internal = p_ptr[i+k] - p_ptr[i+1];
            
            // Calculate how many more zeros we need from the boundary blocks
            long long rem = k2 - internal;
            
            // If we need more zeros than available internally (or exactly enough)
            if (rem >= 0) {
                int L = z_ptr[i];     // Available zeros on left
                int R = z_ptr[i+k];   // Available zeros on right
                
                // We need to choose x zeros from left and y zeros from right
                // such that x + y = rem, with 0 <= x <= L and 0 <= y <= R.
                // Substituting y = rem - x:
                // 0 <= rem - x <= R  =>  rem - R <= x <= rem
                // Combined with 0 <= x <= L:
                // x must be in [max(0, rem - R), min(L, rem)]
                
                long long min_x = rem - R;
                if (min_x < 0) min_x = 0;
                
                long long max_x = L;
                if (rem < max_x) max_x = rem;
                
                long long count = max_x - min_x + 1;
                if (count > 0) {
                    ans += count;
                }
            }
        }
    }

    cout << ans << "\n";

    return 0;
}