#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <ctime>
#include <climits>

using namespace std;

typedef long long ll;

struct Item {
    ll val;
    int id;
};

struct SubsetSum {
    ll sum;
    int mask; 
};

int n;
ll T;
vector<Item> items;
int best_sol[105];
ll min_diff = -1;

// k=44 means split into 22 and 22. 2^22 = 4M.
// Sorting 4M items is fast enough to allow multiple iterations within 2s.
const int K_TARGET = 44;

void check_solution(const vector<int>& sol) {
    ll current_sum = 0;
    for (int i = 0; i < n; ++i) {
        if (sol[i]) current_sum += items[i].val;
    }
    ll diff = abs(current_sum - T);
    if (min_diff == -1 || diff < min_diff) {
        min_diff = diff;
        for (int i = 0; i < n; ++i) best_sol[items[i].id] = sol[i];
    }
}

void solve() {
    // Sort items by value. This helps heuristics for Exp/Pareto distributions
    // by allowing us to pick smaller items for the dense solver part.
    sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
        return a.val < b.val;
    });

    int k = min(n, K_TARGET);
    int half = k / 2;
    int rest = k - half;
    
    // Pre-allocate to save time
    vector<SubsetSum> left_sums;
    vector<SubsetSum> right_sums;
    left_sums.reserve(1 << half);
    right_sums.reserve(1 << rest);

    vector<int> current_config(n, 0);
    check_solution(current_config); // Check empty set

    double start_time = (double)clock() / CLOCKS_PER_SEC;
    double time_limit = 1.85; 

    mt19937 rng(1337);

    while (true) {
        double curr_time = (double)clock() / CLOCKS_PER_SEC;
        if (curr_time - start_time > time_limit) break;

        // We want to select k items to solve optimally (I_solve) and n-k to fix greedily (I_fix).
        // To maximize success, I_solve should contain small numbers (for fine granularity) 
        // AND some larger numbers (to cover range).
        // Strategy: Keep 'keep' smallest items in I_solve. Fill the rest of I_solve randomly.
        
        vector<int> p(n);
        for(int i=0; i<n; ++i) p[i] = i;
        
        int keep = 15; 
        if (keep > k) keep = k;
        
        // Shuffle the indices starting from 'keep' to the end
        shuffle(p.begin() + keep, p.end(), rng);
        
        // I_solve: first k indices of p
        vector<int> idx_solve(k);
        for(int i=0; i<k; ++i) idx_solve[i] = p[i];
        
        // Calculate target for fixed set to center the residual for I_solve
        ll sum_solve_total = 0;
        for (int x : idx_solve) sum_solve_total += items[x].val;
        
        ll target_fix = T - sum_solve_total / 2;
        ll current_fix_sum = 0;
        
        // Reset current configuration
        fill(current_config.begin(), current_config.end(), 0);
        
        // I_fix: remaining indices
        vector<int> idx_fix;
        for(int i=k; i<n; ++i) idx_fix.push_back(p[i]);
        // Shuffle I_fix to vary the greedy choices
        shuffle(idx_fix.begin(), idx_fix.end(), rng);

        // Greedy heuristic for fixed set
        for (int idx : idx_fix) {
            if (abs((current_fix_sum + items[idx].val) - target_fix) < abs(current_fix_sum - target_fix)) {
                current_config[idx] = 1;
                current_fix_sum += items[idx].val;
            }
        }
        
        // Target for the MITM solver
        ll target_solve = T - current_fix_sum;
        
        // Meet-in-the-middle on I_solve
        left_sums.clear();
        right_sums.clear();
        
        // Generate Left sums
        int left_size = 1 << half;
        for (int m = 0; m < left_size; ++m) {
            ll s = 0;
            for (int bit = 0; bit < half; ++bit) {
                if ((m >> bit) & 1) s += items[idx_solve[bit]].val;
            }
            left_sums.push_back({s, m});
        }
        
        // Generate Right sums
        int right_size = 1 << rest;
        for (int m = 0; m < right_size; ++m) {
            ll s = 0;
            for (int bit = 0; bit < rest; ++bit) {
                if ((m >> bit) & 1) s += items[idx_solve[half + bit]].val;
            }
            right_sums.push_back({s, m});
        }
        
        // Sort Right sums for binary search
        sort(right_sums.begin(), right_sums.end(), [](const SubsetSum& a, const SubsetSum& b) {
            return a.sum < b.sum;
        });
        
        // Search
        for (const auto& l : left_sums) {
            ll need = target_solve - l.sum;
            
            auto it = lower_bound(right_sums.begin(), right_sums.end(), need, [](const SubsetSum& a, ll val) {
                return a.sum < val;
            });
            
            // Check current iterator and previous one
            auto check_and_update = [&](const SubsetSum& r) {
                ll total = l.sum + r.sum;
                ll diff = abs(total - target_solve);
                if (diff == 0 || min_diff == -1 || diff < min_diff) {
                    // Update global best
                    // Reset bits for solve set in current_config first (clean state)
                    for(int x : idx_solve) current_config[x] = 0;
                    
                    for (int bit = 0; bit < half; ++bit) 
                        if ((l.mask >> bit) & 1) current_config[idx_solve[bit]] = 1;
                    for (int bit = 0; bit < rest; ++bit) 
                        if ((r.mask >> bit) & 1) current_config[idx_solve[half + bit]] = 1;
                    
                    check_solution(current_config);
                    return diff == 0;
                }
                return false;
            };

            if (it != right_sums.end()) {
                if (check_and_update(*it)) return; 
            }
            if (it != right_sums.begin()) {
                if (check_and_update(*prev(it))) return;
            }
        }
        
        if (min_diff == 0) break;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n >> T)) return 0;
    items.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> items[i].val;
        items[i].id = i;
    }
    
    solve();
    
    for (int i = 0; i < n; ++i) cout << best_sol[i];
    cout << endl;
    
    return 0;
}