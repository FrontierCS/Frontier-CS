#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <algorithm>

// __builtin_ctz and __builtin_popcount are standard in competitive programming environments (GCC/Clang)

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;
    std::vector<std::string> s(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> s[i];
    }
    
    // Remove duplicate patterns as they are redundant for the union operation.
    std::sort(s.begin(), s.end());
    s.erase(std::unique(s.begin(), s.end()), s.end());
    m = s.size();

    int num_masks = 1 << m;
    std::vector<std::string> merged_pattern(num_masks);
    std::vector<bool> is_compatible(num_masks);
    std::vector<int> p_count(num_masks);
    
    merged_pattern[0].assign(n, '?');
    is_compatible[0] = true;
    p_count[0] = 0;
    
    for (int mask = 1; mask < num_masks; ++mask) {
        int lsb_idx = __builtin_ctz(mask);
        int prev_mask = mask ^ (1 << lsb_idx);
        
        if (!is_compatible[prev_mask]) {
            is_compatible[mask] = false;
            continue;
        }
        
        is_compatible[mask] = true;
        int current_p = 0;
        
        std::string& current_merged = merged_pattern[mask];
        current_merged.resize(n);
        
        const std::string& prev_merged = merged_pattern[prev_mask];
        const std::string& new_s = s[lsb_idx];

        for (int j = 0; j < n; ++j) {
            char c1 = prev_merged[j];
            char c2 = new_s[j];
            
            char res_char;
            if (c1 == '?') {
                res_char = c2;
            } else if (c2 == '?') {
                res_char = c1;
            } else if (c1 != c2) {
                is_compatible[mask] = false;
                break;
            } else { // c1 == c2
                res_char = c1;
            }
            
            current_merged[j] = res_char;
            if (res_char != '?') {
                current_p++;
            }
        }
        
        if (is_compatible[mask]) {
            p_count[mask] = current_p;
        }
    }
    
    long double probability = 0.0L;
    
    std::vector<long double> pow_025(n + 1);
    pow_025[0] = 1.0L;
    for (int i = 1; i <= n; ++i) {
        pow_025[i] = pow_025[i-1] * 0.25L;
    }

    for (int mask = 1; mask < num_masks; ++mask) {
        if (is_compatible[mask]) {
            long double term = pow_025[p_count[mask]];
            if (__builtin_popcount(mask) % 2 == 1) {
                probability += term;
            } else {
                probability -= term;
            }
        }
    }
    
    std::cout << std::fixed << std::setprecision(12) << probability << std::endl;
}

int main() {
    solve();
    return 0;
}