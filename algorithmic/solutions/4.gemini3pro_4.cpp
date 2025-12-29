#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

// Global variables to store state
int N;
long long K;
map<pair<int, int>, long long> memo;
int queries_count = 0;

// Function to perform a query with memoization
long long query(int r, int c) {
    if (r < 1 || r > N || c < 1 || c > N) return 2e18; // Should not happen
    if (memo.count({r, c})) return memo[{r, c}];
    
    // Safety check for query limit
    if (queries_count >= 50000) return 2e18; 

    cout << "QUERY " << r << " " << c << endl;
    long long val;
    cin >> val;
    memo[{r, c}] = val;
    queries_count++;
    return val;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    // lo[i] is the first candidate column in row i
    // hi[i] is the last candidate column in row i
    // Initially all cells are candidates
    vector<int> lo(N + 1, 1);
    vector<int> hi(N + 1, N);
    
    // Random number generator
    mt19937_64 rng(1337);

    while (true) {
        // Identify valid rows and calculate total active size
        long long active_size = 0;
        vector<int> valid_rows;
        for (int i = 1; i <= N; ++i) {
            if (lo[i] <= hi[i]) {
                active_size += (hi[i] - lo[i] + 1);
                valid_rows.push_back(i);
            }
        }

        // Heuristic to switch to final collection
        // If active size is small or we are running out of queries, fetch all remaining candidates
        if (active_size <= 2500 || (50000 - queries_count) <= active_size + 100) {
            vector<long long> candidates;
            candidates.reserve(active_size);
            for (int r : valid_rows) {
                for (int c = lo[r]; c <= hi[r]; ++c) {
                    candidates.push_back(query(r, c));
                }
            }
            sort(candidates.begin(), candidates.end());
            
            // Calculate how many elements strictly smaller than the active set are already counted
            long long smaller_count = 0;
            for (int i = 1; i <= N; ++i) {
                smaller_count += (lo[i] - 1);
            }
            
            long long index = K - smaller_count - 1; 
            if (index < 0) index = 0;
            if (index >= candidates.size()) index = candidates.size() - 1;
            
            cout << "DONE " << candidates[index] << endl;
            return 0;
        }

        // Sampling to pick a good pivot
        int samples_cnt = 25; 
        if (active_size < samples_cnt) samples_cnt = active_size;
        
        vector<long long> samples;
        for (int s = 0; s < samples_cnt; ++s) {
            long long idx = uniform_int_distribution<long long>(0, active_size - 1)(rng);
            // Locate the cell (r, c) corresponding to linear index idx
            int r_idx = -1, c_idx = -1;
            long long current = 0;
            for (int r : valid_rows) {
                long long width = hi[r] - lo[r] + 1;
                if (idx < current + width) {
                    r_idx = r;
                    c_idx = lo[r] + (idx - current);
                    break;
                }
                current += width;
            }
            if (r_idx != -1) samples.push_back(query(r_idx, c_idx));
        }
        sort(samples.begin(), samples.end());

        // Select pivot based on approximate location of K
        long long smaller_count_global = 0;
        for (int i = 1; i <= N; ++i) smaller_count_global += (lo[i] - 1);
        long long needed = K - smaller_count_global;
        
        double ratio = (double)needed / active_size;
        int sample_idx = (int)(ratio * samples.size());
        if (sample_idx < 0) sample_idx = 0;
        if (sample_idx >= samples.size()) sample_idx = samples.size() - 1;
        
        long long pivot = samples[sample_idx];

        // Rank the pivot in the matrix using the saddleback search idea within active region
        long long count_le = 0;
        vector<int> p(N + 1);
        
        int c = N; 
        for (int r = 1; r <= N; ++r) {
            count_le += (lo[r] - 1);
            
            // Limit c by the current row's upper bound (and previous row's c, implicit by loop structure)
            c = min(c, hi[r]);
            
            if (lo[r] > hi[r]) {
                // Inactive row: boundary is fixed at hi[r]
                p[r] = c;
            } else {
                // Active row: find largest c such that a[r][c] <= pivot
                while (c >= lo[r]) {
                    long long val = query(r, c);
                    if (val > pivot) {
                        c--;
                    } else {
                        break;
                    }
                }
                p[r] = c;
                count_le += (c - lo[r] + 1);
            }
        }
        
        // Update boundaries based on pivot rank
        if (count_le < K) {
            // pivot is strictly smaller than answer
            // Discard elements <= pivot (so indices <= p[r])
            for (int r = 1; r <= N; ++r) {
                if (lo[r] <= hi[r])
                    lo[r] = max(lo[r], p[r] + 1);
            }
        } else {
            // pivot is >= answer
            // Discard elements > pivot (so indices > p[r])
            for (int r = 1; r <= N; ++r) {
                if (lo[r] <= hi[r])
                    hi[r] = min(hi[r], p[r]);
            }
        }
    }
    return 0;
}