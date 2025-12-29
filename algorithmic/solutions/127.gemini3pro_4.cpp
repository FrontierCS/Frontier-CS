#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <tuple>
#include <deque>
#include <map>
#include <cstdlib>
#include <ctime>

using namespace std;

// Global variables
int N;
int S_max = -1;
map<int, int> trash_prefix; // Stores a0 (count of better items to left) for trash indices
set<int> visited; // Indices of known 'interesting' items (sum < S_max)
map<int, pair<int, int>> cache_res; // Cache query results

// Function to query a box
// Exits if diamond is found
pair<int, int> query(int i) {
    if (cache_res.count(i)) return cache_res[i];
    cout << "? " << i << endl;
    int a0, a1;
    if (!(cin >> a0 >> a1)) exit(0);
    if (a0 == -1) exit(0); // Error from judge
    cache_res[i] = {a0, a1};
    if (a0 + a1 == 0) {
        cout << "! " << i << endl;
        exit(0);
    }
    return {a0, a1};
}

// Update S_max if a larger sum is found (indicating a cheaper prize type)
bool check_update_smax(int s) {
    if (s > S_max) {
        S_max = s;
        return true;
    }
    return false;
}

struct Task {
    int L, R;
    int expected_cnt; // Number of interesting items in (L, R)
};

int main() {
    // Optimization for I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    srand(time(0));
    if (!(cin >> N)) return 0;

    // 1. Initial Sampling
    // Query a few random indices to establish a baseline S_max.
    // The most common prize type (trash) will have the largest sum.
    int samples = 25; 
    if (N < samples) samples = N;
    
    vector<int> init_indices;
    if (N <= 100) {
        for(int i=0; i<N; ++i) init_indices.push_back(i);
    } else {
        set<int> s;
        while(s.size() < (size_t)samples) {
            int r = rand() % N;
            s.insert(r);
        }
        init_indices.assign(s.begin(), s.end());
    }

    for (int i : init_indices) {
        pair<int, int> res = query(i);
        int s = res.first + res.second;
        if (s > S_max) S_max = s;
    }
    
    // 2. Setup Search
    // Virtual boundaries: -1 (prefix count 0) and N (prefix count S_max)
    trash_prefix[-1] = 0;
    trash_prefix[N] = S_max;
    
    deque<Task> q;
    q.push_back({-1, N, S_max});
    
    // 3. Process Intervals
    while (!q.empty()) {
        Task t = q.front();
        q.pop_front();
        
        int L = t.L;
        int R = t.R;
        int expected = t.expected_cnt;
        
        // Ensure the virtual right boundary N has correct S_max
        if (R == N && trash_prefix[N] != S_max) {
             trash_prefix[N] = S_max;
        }
        
        // Ensure L and R are valid in map (L might be -1, R might be N)
        // If they are regular indices, they must be trash
        // (Logic ensures we only push trash indices as boundaries)

        // Count already found interesting items in (L, R)
        int found = 0;
        auto it = visited.upper_bound(L);
        while (it != visited.end() && *it < R) {
            found++;
            it++;
        }
        
        int remaining = expected - found;
        if (remaining <= 0) continue;
        
        // Heuristic: If interval is small relative to remaining items, scan linearly
        // This handles dense clusters of interesting items
        if (R - L - 1 <= remaining + 2) { 
             for (int i = L + 1; i < R; ++i) {
                 if (visited.count(i)) continue;
                 pair<int, int> res = query(i);
                 int s = res.first + res.second;
                 
                 if (check_update_smax(s)) {
                     // S_max updated, restart search
                     goto restart_search;
                 }
                 
                 if (s < S_max) {
                     visited.insert(i);
                 } else {
                     // Found a trash item, record it
                     trash_prefix[i] = res.first;
                 }
             }
             continue; 
        }
        
        // Split Strategy: Find a trash pivot near mid
        int mid = (L + R) / 2;
        int pivot = -1;
        
        // Alternating search expanding from mid
        for (int d = 0; ; ++d) {
            int candidates[2];
            int c_cnt = 0;
            if (d == 0) candidates[c_cnt++] = mid;
            else {
                if (mid + d < R) candidates[c_cnt++] = mid + d;
                if (mid - d > L) candidates[c_cnt++] = mid - d;
            }
            
            bool found_trash = false;
            bool out_of_bounds = true;
            
            for (int k=0; k<c_cnt; ++k) {
                int p = candidates[k];
                out_of_bounds = false;
                
                if (visited.count(p)) continue;
                
                pair<int, int> res = query(p);
                int s = res.first + res.second;
                
                if (check_update_smax(s)) {
                     goto restart_search;
                }
                
                if (s == S_max) {
                    pivot = p;
                    trash_prefix[p] = res.first;
                    found_trash = true;
                    break;
                } else {
                    visited.insert(p);
                }
            }
            
            if (found_trash) break;
            if (out_of_bounds && d > (R-L)) break; // Should not happen given logic
        }
        
        if (pivot != -1) {
            // Found a trash pivot, split the interval
            int p_pre = trash_prefix[pivot];
            int l_pre = trash_prefix[L];
            int r_pre = trash_prefix[R];
            
            int left_cnt = p_pre - l_pre;
            int right_cnt = r_pre - p_pre;
            
            // Push sub-tasks (Right first to be popped last? Order doesn't matter much)
            q.push_front({pivot, R, right_cnt});
            q.push_front({L, pivot, left_cnt});
        }
        continue;

        restart_search:
        {
            q.clear();
            trash_prefix.clear();
            trash_prefix[-1] = 0;
            trash_prefix[N] = S_max;
            
            // Re-evaluate visited set based on new S_max
            visited.clear();
            for (auto const& [idx, val] : cache_res) {
                if (val.first + val.second < S_max) {
                    visited.insert(idx);
                }
            }
            q.push_back({-1, N, S_max});
        }
    }

    // Fallback if loop finishes without exit (should not happen if diamond exists)
    cout << "! 0" << endl;
    return 0;
}