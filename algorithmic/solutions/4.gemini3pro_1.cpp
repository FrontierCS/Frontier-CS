#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

// Global memoization for queries
// N <= 2000, N^2 = 4,000,000
vector<long long> memo;
int n;
long long k;

// Function to query the matrix
// Uses 1-based indexing for query command, 0-based internally
long long query(int r, int c) {
    if (r < 0 || r >= n || c < 0 || c >= n) return -2; 
    if (memo[r * n + c] != -1) {
        return memo[r * n + c];
    }
    cout << "QUERY " << r + 1 << " " << c + 1 << endl;
    long long val;
    cin >> val;
    memo[r * n + c] = val;
    return val;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> k)) return 0;

    // Allocate memoization array
    memo.assign(n * n, -1);

    // L[i]: first column index in row i that is a candidate
    // R[i]: first column index in row i that is NOT a candidate (candidates are < R[i])
    // Initially all elements are candidates.
    vector<int> L(n, 0);
    vector<int> R(n, n);

    // Random number generator
    mt19937_64 rng(1337);

    while (true) {
        // Count total candidates and prepare to pick a random one
        long long total_candidates = 0;
        for (int i = 0; i < n; ++i) {
            if (L[i] < R[i]) {
                total_candidates += (R[i] - L[i]);
            }
        }

        if (total_candidates == 0) break; // Should theoretically not be reached

        // Pick a random index in [0, total_candidates - 1]
        long long pick = std::uniform_int_distribution<long long>(0, total_candidates - 1)(rng);
        
        int pivot_r = -1, pivot_c = -1;
        long long current_idx = 0;
        
        // Find the coordinates of the picked candidate
        for (int i = 0; i < n; ++i) {
            long long width = R[i] - L[i];
            if (width > 0) {
                if (current_idx + width > pick) {
                    pivot_r = i;
                    pivot_c = L[i] + (int)(pick - current_idx);
                    break;
                }
                current_idx += width;
            }
        }
        
        long long pivot_val = query(pivot_r, pivot_c);

        // Calculate the rank of pivot_val (number of elements <= pivot_val)
        long long count_le = 0;
        vector<int> boundary(n); 
        
        // Start search from top-right-most possible position
        // Since the boundary of <= pivot_val moves left as we go down the rows
        int curr_c = n - 1; 
        
        for (int i = 0; i < n; ++i) {
            // Constrain by previous row's boundary and current row's right limit
            if (i > 0) curr_c = min(curr_c, boundary[i-1]);
            curr_c = min(curr_c, R[i] - 1);
            
            // Move left until we find an element <= pivot_val
            while (curr_c >= L[i]) {
                long long val = query(i, curr_c);
                if (val <= pivot_val) break;
                curr_c--;
            }
            
            boundary[i] = curr_c;
            count_le += (curr_c + 1);
        }
        
        if (count_le >= k) {
            // ans <= pivot_val
            // We can discard all elements > pivot_val.
            // For each row, candidates must be <= pivot_val.
            // The last element <= pivot_val is at boundary[i].
            // So new R[i] should be boundary[i] + 1.
            bool changed = false;
            for (int i = 0; i < n; ++i) {
                if (R[i] > boundary[i] + 1) {
                    R[i] = boundary[i] + 1;
                    changed = true;
                }
            }
            
            // If the search space didn't shrink, it means all remaining candidates are <= pivot_val.
            // Since we picked pivot from candidates, pivot_val is likely the answer.
            if (!changed) {
                cout << "DONE " << pivot_val << endl;
                return 0;
            }
        } else {
            // ans > pivot_val
            // We can discard all elements <= pivot_val.
            // For each row, candidates must be > pivot_val.
            // The last element <= pivot_val is at boundary[i].
            // So new L[i] should be boundary[i] + 1.
            bool changed = false;
            for (int i = 0; i < n; ++i) {
                if (L[i] <= boundary[i]) {
                    L[i] = boundary[i] + 1;
                    changed = true;
                }
            }
        }
    }

    return 0;
}