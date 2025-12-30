#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

long long M = 1e9 + 7;

long long power(long long base, long long exp) {
    long long res = 1;
    base %= M;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % M;
        base = (base * base) % M;
        exp /= 2;
    }
    return res;
}

long long modInverse(long long n) {
    return power(n, M - 2);
}

long long circular_dist(long long a, long long b) {
    long long d = abs(a - b);
    return min(d, M - d);
}

long long score_sets(vector<long long>& A, vector<long long>& B) {
    if (A.empty() || B.empty()) return 0; // Should not happen
    sort(A.begin(), A.end());
    sort(B.begin(), B.end());
    
    // To handle different sizes due to randomness (though we expect ~equal), 
    // we can interpolate or just truncate. With 40 queries, sizes will be around 20.
    // Let's resample or just compare prefixes/suffixes?
    // Better: resize larger to smaller by skipping? 
    // Or just take min size.
    size_t sz = min(A.size(), B.size());
    
    // To minimize artifacts from random size diffs, let's just pick sz elements uniformly?
    // Actually, simple truncation is okay if randomized.
    // Or better: resample to size 20 fixed?
    // Given the constraints and randomness, simple matching of min size is robust enough.
    
    // Actually, comparing sorted arrays element-wise is sensitive to shifts.
    // A better robust metric for "same distribution" is sum of squared differences of percentiles?
    // Let's just use the min size.
    
    long long total_dist = 0;
    
    // We can align them best we can. 
    // Since distributions should be identical, just comparing A[i] and B[i] (scaled indices) works.
    for (size_t i = 0; i < sz; ++i) {
        // Map index i from smaller set to larger set?
        // Let's just compare A[i] and B[i] for i < sz.
        // It assumes 1 and 2 are uniformly distributed in indices, which they are.
        total_dist += circular_dist(A[i], B[i]);
    }
    return total_dist;
}

int main() {
    int n;
    if (!(cin >> n)) return 0;

    int Q = 40;
    if (n > 400 && Q > 38) Q = 38; // Safety for time? No, Q<=40 is strict for scoring. 40 is fine.
    // Wait, problem says Q<=40 for full score. Let's use 40.
    Q = 40;

    // Generate queries
    // Use inputs 1 and 2.
    vector<vector<int>> queries(Q, vector<int>(n + 1));
    mt19937 rng(1337); 
    uniform_int_distribution<int> dist(1, 2);

    for (int i = 0; i < Q; ++i) {
        for (int j = 0; j <= n; ++j) {
            queries[i][j] = dist(rng);
        }
    }

    // Output queries
    vector<long long> results(Q);
    for (int i = 0; i < Q; ++i) {
        cout << "?";
        for (int j = 0; j <= n; ++j) {
            cout << " " << queries[i][j];
        }
        cout << endl;
        cin >> results[i];
    }

    vector<int> ops(n + 1); // 1-based index for ops, ops[i] stores 0 (+) or 1 (x)
    
    // Current values derived from results, peeling from right
    vector<long long> current_vals = results;

    long long inv2 = modInverse(2);

    for (int k = n; k >= 1; --k) {
        vector<long long> S1_idx, S2_idx;
        for (int i = 0; i < Q; ++i) {
            if (queries[i][k] == 1) S1_idx.push_back(i);
            else S2_idx.push_back(i);
        }

        // Hyp +
        vector<long long> vals_plus_1, vals_plus_2;
        for (long long idx : S1_idx) {
            long long v = (current_vals[idx] - 1 + M) % M;
            vals_plus_1.push_back(v);
        }
        for (long long idx : S2_idx) {
            long long v = (current_vals[idx] - 2 + M) % M;
            vals_plus_2.push_back(v);
        }
        long long score_plus = score_sets(vals_plus_1, vals_plus_2);

        // Hyp x
        vector<long long> vals_mult_1, vals_mult_2;
        for (long long idx : S1_idx) {
            long long v = current_vals[idx];
            vals_mult_1.push_back(v);
        }
        for (long long idx : S2_idx) {
            long long v = (current_vals[idx] * inv2) % M;
            vals_mult_2.push_back(v);
        }
        long long score_mult = score_sets(vals_mult_1, vals_mult_2);

        if (score_plus < score_mult) {
            ops[k] = 0; // +
            for (int i = 0; i < Q; ++i) {
                current_vals[i] = (current_vals[i] - queries[i][k] + M) % M;
            }
        } else {
            ops[k] = 1; // x
            for (int i = 0; i < Q; ++i) {
                if (queries[i][k] == 1) {
                    // val / 1 = val
                } else {
                    current_vals[i] = (current_vals[i] * inv2) % M;
                }
            }
        }
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ops[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}