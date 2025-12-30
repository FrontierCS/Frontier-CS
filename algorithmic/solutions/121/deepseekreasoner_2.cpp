#include <iostream>
#include <vector>
#include <array>
#include <cmath>
#include <iomanip>
#include <cstdint>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    int wordCount = (n + 63) / 64;  // number of 64-bit words needed to represent n bits
    
    // For each pattern, store 4 masks (one per nucleotide)
    vector<array<vector<uint64_t>, 4>> patterns(m);
    for (int i = 0; i < m; ++i) {
        for (int l = 0; l < 4; ++l) {
            patterns[i][l].resize(wordCount, 0);
        }
        string s;
        cin >> s;
        for (int j = 0; j < n; ++j) {
            char c = s[j];
            int letter = -1;
            if (c == 'A') letter = 0;
            else if (c == 'C') letter = 1;
            else if (c == 'G') letter = 2;
            else if (c == 'T') letter = 3;
            // '?' leaves letter = -1, no mask set
            if (letter != -1) {
                int wordIdx = j / 64;
                int bitIdx = j % 64;
                patterns[i][letter][wordIdx] |= (1ULL << bitIdx);
            }
        }
    }
    
    // Precompute 4^{-d} for d = 0..n
    vector<long double> pow4inv(n + 1);
    pow4inv[0] = 1.0L;
    for (int d = 1; d <= n; ++d) {
        pow4inv[d] = pow4inv[d-1] / 4.0L;
    }
    
    long double total = 0.0L;
    int totalSubsets = 1 << m;
    
    // Iterate over all non-empty subsets of patterns
    for (int mask = 1; mask < totalSubsets; ++mask) {
        int size = __builtin_popcount(mask);
        long double sign = (size % 2 == 1) ? 1.0L : -1.0L;
        
        // Accumulate masks for the four letters over all patterns in the subset
        array<vector<uint64_t>, 4> acc;
        for (int l = 0; l < 4; ++l) {
            acc[l].resize(wordCount, 0);
        }
        
        for (int i = 0; i < m; ++i) {
            if (mask & (1 << i)) {
                for (int l = 0; l < 4; ++l) {
                    for (int w = 0; w < wordCount; ++w) {
                        acc[l][w] |= patterns[i][l][w];
                    }
                }
            }
        }
        
        // Check for conflicts: no position should be fixed to two different letters
        bool conflict = false;
        for (int l1 = 0; l1 < 4 && !conflict; ++l1) {
            for (int l2 = l1 + 1; l2 < 4; ++l2) {
                for (int w = 0; w < wordCount; ++w) {
                    if (acc[l1][w] & acc[l2][w]) {
                        conflict = true;
                        break;
                    }
                }
                if (conflict) break;
            }
        }
        if (conflict) continue;
        
        // Compute the number of positions fixed by at least one pattern in the subset
        int fixed_pos = 0;
        for (int w = 0; w < wordCount; ++w) {
            uint64_t overall_word = 0;
            for (int l = 0; l < 4; ++l) {
                overall_word |= acc[l][w];
            }
            fixed_pos += __builtin_popcountll(overall_word);
        }
        
        // Add the contribution of this subset
        total += sign * pow4inv[fixed_pos];
    }
    
    cout << fixed << setprecision(15) << total << endl;
    return 0;
}