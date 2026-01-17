#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int MAX_N = 105;
const double TIME_LIMIT = 0.85; 

// Global variables
int n;
long long T;
long long A[MAX_N];
int best_sol[MAX_N];
long long min_error = -1;

// Random number generator
mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

// Update global best solution
void update_solution(const vector<int>& sol) {
    long long current_sum = 0;
    for (int i = 0; i < n; ++i) {
        if (sol[i]) current_sum += A[i];
    }
    long long error = abs(current_sum - T);
    
    if (min_error == -1 || error < min_error) {
        min_error = error;
        for (int i = 0; i < n; ++i) best_sol[i] = sol[i];
    }
}

// Local optimization: optimize a subset of K variables using Meet-in-the-middle
// Keeps the assignment of other variables fixed.
void solve_subproblem(vector<int>& current_assignment, const vector<int>& indices) {
    int k = indices.size();
    if (k == 0) return;

    // Calculate sum of the fixed variables
    long long current_total = 0;
    for (int i = 0; i < n; ++i) {
        if (current_assignment[i]) current_total += A[i];
    }
    
    long long fixed_sum = current_total;
    for (int idx : indices) {
        if (current_assignment[idx]) fixed_sum -= A[idx];
    }

    // We want local_sum + fixed_sum approx T
    // So local_sum approx T - fixed_sum
    long long target = T - fixed_sum;
    
    // Split varying indices into two halves for MITM
    int mid = k / 2;
    int left_cnt = mid;
    int right_cnt = k - mid;
    
    int left_states = 1 << left_cnt;
    vector<pair<long long, int>> left_sums(left_states);
    
    // Generate left sums
    for (int m = 0; m < left_states; ++m) {
        long long s = 0;
        for (int i = 0; i < left_cnt; ++i) {
            if ((m >> i) & 1) s += A[indices[i]];
        }
        left_sums[m] = {s, m};
    }
    
    sort(left_sums.begin(), left_sums.end());
    
    int right_states = 1 << right_cnt;
    
    long long local_best_err = -1;
    int best_left_mask = 0;
    int best_right_mask = 0;
    
    // Iterate right sums and match with left
    for (int m = 0; m < right_states; ++m) {
        long long s_right = 0;
        for (int i = 0; i < right_cnt; ++i) {
            if ((m >> i) & 1) s_right += A[indices[mid + i]];
        }
        
        long long needed = target - s_right;
        
        // Find closest in left_sums
        auto it = lower_bound(left_sums.begin(), left_sums.end(), make_pair(needed, -1));
        
        // Check current iterator
        if (it != left_sums.end()) {
            long long total = s_right + it->first;
            long long err = abs(total - target);
            if (local_best_err == -1 || err < local_best_err) {
                local_best_err = err;
                best_left_mask = it->second;
                best_right_mask = m;
            }
        }
        // Check previous iterator
        if (it != left_sums.begin()) {
            auto it2 = prev(it);
            long long total = s_right + it2->first;
            long long err = abs(total - target);
            if (local_best_err == -1 || err < local_best_err) {
                local_best_err = err;
                best_left_mask = it2->second;
                best_right_mask = m;
            }
        }
        
        if (local_best_err == 0) break;
    }
    
    // Update current_assignment with the best local configuration
    for (int i = 0; i < left_cnt; ++i) {
        current_assignment[indices[i]] = (best_left_mask >> i) & 1;
    }
    for (int i = 0; i < right_cnt; ++i) {
        current_assignment[indices[mid + i]] = (best_right_mask >> i) & 1;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n >> T)) return 0;
    for (int i = 0; i < n; ++i) {
        cin >> A[i];
    }
    
    auto start_time = chrono::steady_clock::now();
    
    // Initial random solution
    vector<int> current_sol(n);
    for (int i = 0; i < n; ++i) current_sol[i] = rng() % 2;
    update_solution(current_sol);
    
    if (min_error == 0) {
        for (int i = 0; i < n; ++i) cout << best_sol[i];
        cout << endl;
        return 0;
    }
    
    // Determine subset size K for LNS
    int K = 24; 
    if (n < K) K = n;
    
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);
    
    // Large Neighborhood Search loop
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > TIME_LIMIT) break;
        
        // Pick a random subset of variables
        shuffle(p.begin(), p.end(), rng);
        
        vector<int> subset_indices;
        subset_indices.reserve(K);
        for(int i=0; i<K; ++i) subset_indices.push_back(p[i]);
        
        // Solve optimally for this subset while fixing others
        solve_subproblem(current_sol, subset_indices);
        
        // Update global best
        update_solution(current_sol);
        
        if (min_error == 0) break;
    }
    
    for (int i = 0; i < n; ++i) cout << best_sol[i];
    cout << endl;
    
    return 0;
}