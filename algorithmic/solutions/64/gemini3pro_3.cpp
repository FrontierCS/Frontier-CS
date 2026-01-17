#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <climits>
#include <numeric>

using namespace std;

// High precision timer setup
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

typedef long long ll;
typedef unsigned long long ull;

// Structure to represent a subset sum state
struct State {
    ll sum;
    ull mask; // Bitmask representing the subset selection
};

// Comparator for sorting states by sum
bool operator<(const State& a, const State& b) {
    return a.sum < b.sum;
}

int n;
ll T;
vector<ll> a;
vector<int> p; // Permutation vector for shuffling indices

// Global best solution tracking
string best_sol;
ll best_diff = -1;

// Update the global best solution if the current one is better
void update_solution(const string& sol, ll sum) {
    ll diff = abs(T - sum);
    if (best_diff == -1 || diff < best_diff) {
        best_diff = diff;
        best_sol = sol;
    }
}

// Function to generate subsets
// indices: list of indices from the original array 'a' to consider
// limit_count: maximum number of subsets to generate (for random sampling)
// exact: if true, generate all possible subsets (2^k); otherwise, random sample
void generate_subsets(const vector<int>& indices, int limit_count, bool exact, vector<State>& out) {
    out.clear();
    int k = indices.size();
    
    // Random generator (static for performance)
    static mt19937_64 rng(1337); 

    if (exact) {
        // Enumerate all subsets
        ll total = (1ULL << k);
        out.resize(total);
        for (ll i = 0; i < total; ++i) {
            ll s = 0;
            for (int j = 0; j < k; ++j) {
                if ((i >> j) & 1) {
                    s += a[indices[j]];
                }
            }
            out[i] = {s, (ull)i};
        }
    } else {
        // Randomly sample subsets
        out.resize(limit_count);
        for (int i = 0; i < limit_count; ++i) {
            ll s = 0;
            ull m = 0;
            ull rand_bits = rng(); // Get 64 random bits
            for(int j=0; j<k; ++j) {
                if((rand_bits >> j) & 1) {
                    s += a[indices[j]];
                    m |= (1ULL << j);
                }
            }
            out[i] = {s, m};
        }
    }
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> T)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    // Initialize with a simple greedy approach
    string current_sol(n, '0');
    ll current_sum = 0;
    for (int i = 0; i < n; ++i) {
        if (current_sum + a[i] <= T) {
            current_sum += a[i];
            current_sol[i] = '1';
        }
    }
    update_solution(current_sol, current_sum);

    // Prepare for randomized iterative improvement
    p.resize(n);
    iota(p.begin(), p.end(), 0);

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Time limit safety buffer (assume 2.0s standard limit, stop at 1.8s)
    double TIME_LIMIT = 1.8; 
    // Size of generated lists. 2^19 approx 524k.
    const int MAX_LIST_SIZE = (1 << 19); 
    // Threshold for switching from exact enumeration to random sampling
    const int EXACT_THRESHOLD = 19;

    // Randomized Meet-in-the-Middle (MITM) Loop
    while (get_elapsed_time() < TIME_LIMIT) {
        // Shuffle indices to explore different partitions of the array
        shuffle(p.begin(), p.end(), rng);

        int mid = n / 2;
        vector<int> left_indices, right_indices;
        left_indices.reserve(mid);
        right_indices.reserve(n - mid);
        
        for(int i=0; i<mid; ++i) left_indices.push_back(p[i]);
        for(int i=mid; i<n; ++i) right_indices.push_back(p[i]);

        // Determine if we should enumerate exactly or sample randomly
        bool exact_left = (left_indices.size() <= EXACT_THRESHOLD);
        bool exact_right = (right_indices.size() <= EXACT_THRESHOLD);

        vector<State> states_left, states_right;
        
        generate_subsets(left_indices, MAX_LIST_SIZE, exact_left, states_left);
        generate_subsets(right_indices, MAX_LIST_SIZE, exact_right, states_right);

        // Sort the right list to enable binary search
        sort(states_right.begin(), states_right.end());

        // For each subset sum in the left half, find the closest complementary sum in the right half
        for (const auto& L : states_left) {
            ll target_R = T - L.sum;
            
            // Find the first element >= target_R
            auto it = lower_bound(states_right.begin(), states_right.end(), State{target_R, 0});
            
            // Check the found element
            if (it != states_right.end()) {
                ll total = L.sum + it->sum;
                ll diff = abs(T - total);
                
                if (best_diff == -1 || diff < best_diff) {
                    string s(n, '0');
                    for(size_t i=0; i<left_indices.size(); ++i) {
                        if((L.mask >> i) & 1) s[left_indices[i]] = '1';
                    }
                    for(size_t i=0; i<right_indices.size(); ++i) {
                        if((it->mask >> i) & 1) s[right_indices[i]] = '1';
                    }
                    update_solution(s, total);
                    if (best_diff == 0) goto end_search;
                }
            }
            
            // Check the element immediately before (if it exists) as it might be closer
            if (it != states_right.begin()) {
                auto prev_it = prev(it);
                ll total = L.sum + prev_it->sum;
                ll diff = abs(T - total);
                
                if (best_diff == -1 || diff < best_diff) {
                    string s(n, '0');
                    for(size_t i=0; i<left_indices.size(); ++i) {
                        if((L.mask >> i) & 1) s[left_indices[i]] = '1';
                    }
                    for(size_t i=0; i<right_indices.size(); ++i) {
                        if((prev_it->mask >> i) & 1) s[right_indices[i]] = '1';
                    }
                    update_solution(s, total);
                    if (best_diff == 0) goto end_search;
                }
            }
        }
    }

    end_search:
    cout << best_sol << endl;

    return 0;
}