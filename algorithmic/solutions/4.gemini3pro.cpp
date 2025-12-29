#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

// Global limits and state
int N;
long long K;
int query_count = 0;
const int QUERY_LIMIT = 50000;

// Cache to store query results to avoid redundant queries
// Key: r * N + c (0-based)
map<long long, long long> cache_map;

// Function to query the matrix
// Using 0-based indexing for logic, converting to 1-based for I/O
long long query(int r, int c) {
    // Basic bounds check, though logic should prevent out of bounds
    if (r < 0 || r >= N || c < 0 || c >= N) return -2e18; 
    
    long long key = (long long)r * N + c;
    if (cache_map.count(key)) {
        return cache_map[key];
    }
    
    // Safety break to respect query limits
    if (query_count >= QUERY_LIMIT) {
        return -1; 
    }

    cout << "QUERY " << r + 1 << " " << c + 1 << endl;
    long long val;
    cin >> val;
    query_count++;
    cache_map[key] = val;
    return val;
}

void answer(long long ans) {
    cout << "DONE " << ans << endl;
    exit(0);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    // L[i] and R[i] define the range of active columns [L[i], R[i]] for row i
    vector<int> L(N, 0);
    vector<int> R(N, N - 1);
    
    // cnt_less tracks the number of elements definitely smaller than the current active region
    // i.e., elements in regions discarded because they were "too small"
    long long cnt_less = 0; 

    // Random number generator
    mt19937_64 rng(1337);

    while (true) {
        // Calculate total active cells and build prefix sums for random sampling
        long long total_active = 0;
        vector<long long> prefix_active(N + 1, 0);
        for (int i = 0; i < N; ++i) {
            if (L[i] <= R[i]) {
                total_active += (R[i] - L[i] + 1);
            }
            prefix_active[i+1] = total_active;
        }

        if (total_active == 0) {
            break;
        }

        // Pick a pivot uniformly at random from active cells
        long long rand_idx = rng() % total_active;
        int pivot_r = -1, pivot_c = -1;
        
        // Find the row for rand_idx
        int row_idx = lower_bound(prefix_active.begin(), prefix_active.end(), rand_idx + 1) - prefix_active.begin() - 1;
        pivot_r = row_idx;
        long long offset = rand_idx - prefix_active[row_idx];
        pivot_c = L[pivot_r] + offset;

        long long pivot_val = query(pivot_r, pivot_c);

        // Pass 1: Count elements <= pivot_val in the whole matrix
        // We only scan through the active region effectively.
        // Elements left of L[i] are known to be < pivot_val (since pivot is from active region).
        // Elements right of R[i] are known to be > pivot_val.
        
        vector<int> S_le(N); // S_le[i] is the column index of the last element <= pivot_val in row i
        long long count_le = 0; // Count of elements <= pivot_val within active region
        int curr_c = N - 1; 
        
        // Due to monotonicity, S_le[i+1] <= S_le[i]. We can initialize curr_c based on R[0].
        if (N > 0) curr_c = R[0];
        
        for (int i = 0; i < N; ++i) {
            if (curr_c > R[i]) curr_c = R[i];
            
            // Move left to find the boundary
            while (curr_c >= L[i]) {
                long long val = query(i, curr_c);
                if (val > pivot_val) {
                    curr_c--;
                } else {
                    break;
                }
            }
            
            S_le[i] = curr_c;
            if (curr_c >= L[i]) {
                count_le += (curr_c - L[i] + 1);
            }
        }
        
        // Total elements <= pivot_val is sum of previously discarded small elements + found in active
        long long total_le = cnt_less + count_le;

        if (total_le < K) {
            // pivot_val is strictly smaller than the Target.
            // All elements <= pivot_val can be discarded.
            // The active region boundaries L[i] move right.
            cnt_less = total_le; 
            for (int i = 0; i < N; ++i) {
                L[i] = max(L[i], S_le[i] + 1);
            }
        } else {
            // Target <= pivot_val.
            // We need to check if Target < pivot_val or Target == pivot_val.
            // Pass 2: Count elements < pivot_val (strictly less)
            
            vector<int> S_lt(N); // S_lt[i] is the column index of the last element < pivot_val
            long long count_lt = 0;
            if (N > 0) curr_c = R[0]; 
            
            for (int i = 0; i < N; ++i) {
                if (curr_c > R[i]) curr_c = R[i];
                
                while (curr_c >= L[i]) {
                    long long val = query(i, curr_c);
                    if (val >= pivot_val) { // Treat equal as "too big" for strictly less count
                        curr_c--;
                    } else {
                        break;
                    }
                }
                S_lt[i] = curr_c;
                if (curr_c >= L[i]) {
                    count_lt += (curr_c - L[i] + 1);
                }
            }
            
            long long total_lt = cnt_less + count_lt;
            
            if (K <= total_lt) {
                // Target < pivot_val.
                // Eliminate elements >= pivot_val.
                // The active region boundaries R[i] move left.
                for (int i = 0; i < N; ++i) {
                    R[i] = min(R[i], S_lt[i]);
                }
            } else {
                // total_lt < K <= total_le
                // This implies Target == pivot_val.
                answer(pivot_val);
            }
        }
    }

    return 0;
}