#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

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
    
    // Store positions of '1's.
    // p[i] will store the index of the i-th '1' (1-based indexing for logic).
    // We add sentinels: p[0] = -1 and p[m+1] = n.
    vector<int> p;
    p.reserve(n + 2);
    p.push_back(-1);
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            p.push_back(i);
        }
    }
    p.push_back(n);

    int m = (int)p.size() - 2; // number of '1's
    int z_tot = n - m;         // number of '0's

    long long ans = 0;

    // We iterate over the number of '1's in the substring, denoted by k.
    // For a substring to satisfy the condition, the number of '0's must be k^2.
    // Thus, the total length of the substring must be k^2 + k.
    // Constraints:
    // 1. k <= m (we cannot have more '1's than available in the string)
    // 2. k^2 <= z_tot (we cannot have more '0's than available in the string)
    
    // The loop iterates while k*k <= z_tot and k <= m.
    // Complexity analysis: The worst case complexity is roughly O(N * sqrt(N)) but with a small constant
    // factor due to the bounds on k^2 and m. Specifically, it maximizes around 0.38 * N * sqrt(N),
    // which for N = 2*10^6 is roughly 10^9 very simple operations. With O3 and AVX2, this fits in time.
    
    for (int k = 1; k * k <= z_tot && k <= m; ++k) {
        int L = k * k + k;
        
        // We consider all windows containing exactly k ones.
        // Let the ones in the window be the i-th to (i+k-1)-th ones.
        // The indices in p corresponding to these are p[i] to p[i+k-1].
        // The window of the substring must start after p[i-1] and end before p[i+k].
        
        // Precompute offsets
        int offset_l2 = L - 1;
        int offset_r2 = L;
        
        int max_i = m - k + 1;
        const int* p_ptr = p.data();

        for (int i = 1; i <= max_i; ++i) {
            // Determine the valid range of start positions for the substring.
            
            // Condition 1: The substring must contain the '1' at p[i].
            // Start position must be > p[i-1] and <= p[i].
            // Range 1: [p[i-1] + 1, p[i]]
            int l1 = p_ptr[i-1] + 1;
            int r1 = p_ptr[i];

            // Condition 2: The substring must contain the '1' at p[i+k-1] and NO '1' at p[i+k].
            // End position `e` must be >= p[i+k-1] and < p[i+k].
            // Since length is fixed to L, start position `s` = `e` - L + 1.
            // s >= p[i+k-1] - L + 1  and  s < p[i+k] - L + 1
            // Range 2: [p[i+k-1] - L + 1, p[i+k] - L]
            int l2 = p_ptr[i+k-1] - offset_l2;
            int r2 = p_ptr[i+k] - offset_r2;

            // Compute intersection of [l1, r1] and [l2, r2]
            int start = (l1 > l2) ? l1 : l2;
            int end = (r1 < r2) ? r1 : r2;

            if (start <= end) {
                ans += (end - start + 1);
            }
        }
    }

    cout << ans << "\n";

    return 0;
}