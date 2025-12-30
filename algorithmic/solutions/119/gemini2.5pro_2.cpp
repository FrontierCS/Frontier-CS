#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <map>
#include <algorithm>

using namespace std;

// The modulus for all calculations
long long M = 1e9 + 7;

// Function to send a query and receive the result
long long query(const vector<long long>& a) {
    cout << "?";
    for (long long x : a) {
        cout << " " << x;
    }
    cout << endl;
    long long response;
    cin >> response;
    return response;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> ops(n);
    int b = 15; // Block size
    int num_blocks = (n + b - 1) / b;

    int ops_found_count = 0;

    for (int i = 0; i < num_blocks; ++i) {
        int start_idx_0based = ops_found_count;
        int end_idx_0based = min(n - 1, ops_found_count + b - 1);
        int block_sz = end_idx_0based - start_idx_0based + 1;

        if (block_sz <= 0) continue;

        // Calculate the initial value K before the current block
        long long K;
        if (i == 0) {
            K = 2; // For the first block, the initial value is just a_0
        } else {
            long long R = 2;
            // Based on previously found operators
            for (int j = 0; j < start_idx_0based; ++j) {
                if (ops[j] == 0) { // +
                    R++;
                }
                // for *, R = R * 1, which is R
            }
            K = R;
        }

        // Construct the query vector 'a'
        vector<long long> a(n + 1);
        a[0] = 2;
        for (int j = 1; j <= n; ++j) {
            a[j] = 1;
        }
        
        long long A = 3; // A constant to distinguish operators
        for (int j = start_idx_0based; j <= end_idx_0based; ++j) {
            a[j + 1] = A;
        }

        // Make the query
        long long V = query(a);

        // Maximum possible contribution from operators after the block
        int c_max = n - 1 - end_idx_0based;

        // Precompute results for all 2^block_sz operator combinations
        map<long long, int> val_to_mask;
        for (int m = 0; m < (1 << block_sz); ++m) {
            long long current_val = K;
            for (int j = 0; j < block_sz; ++j) {
                if ((m >> j) & 1) { // op is * (1)
                    current_val = (current_val * A) % M;
                } else { // op is + (0)
                    current_val = (current_val + A) % M;
                }
            }
            val_to_mask[current_val] = m;
        }
        
        // Find the matching operator sequence
        for (int c = 0; c <= c_max; ++c) {
            long long target = (V - c + M) % M;
            if (val_to_mask.count(target)) {
                int m = val_to_mask[target];
                for (int j = 0; j < block_sz; ++j) {
                    ops[start_idx_0based + j] = (m >> j) & 1;
                }
                break;
            }
        }
        
        ops_found_count = end_idx_0based + 1;
    }

    // Output the final answer
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << ops[i];
    }
    cout << endl;

    return 0;
}