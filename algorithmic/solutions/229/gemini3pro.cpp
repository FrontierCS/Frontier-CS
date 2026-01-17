#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Standard LIS on a vector
int compute_lis(const vector<long long>& v) {
    if (v.empty()) return 0;
    vector<long long> tails;
    tails.reserve(v.size());
    for (long long x : v) {
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) {
            tails.push_back(x);
        } else {
            *it = x;
        }
    }
    return tails.size();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    long long x;
    if (!(cin >> n >> x)) return 0;

    vector<long long> t(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    // cuts[k] is the starting index of the k-th block (0-based)
    // We have 11 blocks, so 10 cuts splitting the array.
    // The optimized variables are cuts[0]...cuts[9].
    vector<int> cuts(10);
    for (int i = 0; i < 10; ++i) {
        cuts[i] = (long long)(i + 1) * n / 11;
    }

    // Preallocate memory for buffers to avoid reallocation overhead
    vector<int> P(n + 1), S(n + 1);
    vector<long long> tails, heads;
    tails.reserve(n);
    heads.reserve(n);

    int iterations = 12; 

    for (int iter = 0; iter < iterations; ++iter) {
        // Sequentially optimize each cut position
        // cuts[k] separates block k and block k+1
        // Range for cuts[k] is [cuts[k-1], cuts[k+1]] (with boundary handling)
        
        for (int k = 0; k < 10; ++k) {
            int L = (k == 0) ? 0 : cuts[k-1];
            int R = (k == 9) ? n : cuts[k+1];
            
            // We want to optimize the split point m in [L, R]
            // Left interval: [L, m-1], Right interval: [m, R-1]
            
            int len = R - L;
            if (len == 0) {
                cuts[k] = L;
                continue;
            }

            // P[i] = LIS length of t[L ... L+i]
            tails.clear();
            for (int i = 0; i < len; ++i) {
                long long val = t[L + i];
                auto it = lower_bound(tails.begin(), tails.end(), val);
                if (it == tails.end()) tails.push_back(val);
                else *it = val;
                P[i] = tails.size();
            }

            // S[i] = LIS length of t[L+i ... R-1]
            // This is equivalent to Longest Decreasing Subsequence on reversed array, 
            // or finding longest chain to the right starting with value > current.
            heads.clear();
            for (int i = len - 1; i >= 0; --i) {
                long long val = t[L + i];
                // We use negated values to use standard LIS logic with lower_bound
                long long neg_val = -val;
                auto it = lower_bound(heads.begin(), heads.end(), neg_val);
                if (it == heads.end()) heads.push_back(neg_val);
                else *it = neg_val;
                S[i] = heads.size();
            }
            
            int best_m = L;
            int max_score = -1;
            
            // Try split point at L + i
            // i goes from 0 to len
            // Left part len i (indices 0..i-1), Right part len len-i (indices i..len-1)
            
            for (int i = 0; i <= len; ++i) {
                int current_score = 0;
                if (i > 0) current_score += P[i-1];
                if (i < len) current_score += S[i];
                
                if (current_score > max_score) {
                    max_score = current_score;
                    best_m = L + i;
                }
            }
            
            cuts[k] = best_m;
        }
    }

    // Apply the operations based on the optimal cuts
    // Op k applies to [cuts[k], n-1] with value x
    // This creates a staircase effect: Block i gets shifted by i*x
    vector<long long> final_t = t;
    for (int k = 0; k < 10; ++k) {
        int start = cuts[k];
        for (int i = start; i < n; ++i) {
            final_t[i] += x;
        }
    }
    
    int ans = compute_lis(final_t);
    
    cout << ans << "\n";
    for (int k = 0; k < 10; ++k) {
        int l = cuts[k] + 1; // Convert to 1-based index
        int r = n;
        // Output valid intervals only
        if (l > n) {
            cout << "1 1 0\n";
        } else {
            cout << l << " " << r << " " << x << "\n";
        }
    }

    return 0;
}