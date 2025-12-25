#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

// Function to solve a single test case
void solve();

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}

// Global variables for a single test case
int n;
std::vector<int> candidates;
std::vector<int> state_masks;

// state_masks bits correspond to (h,d) states:
// 0: (0,0) - initial state
// 1: (1,0) - one consecutive honest
// 2: (2,0) - two consecutive honest
// 3: (0,1) - one consecutive dishonest
// 4: (0,2) - two consecutive dishonest

int do_query(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int x;
    std::cin >> x;
    return x;
}

void update(int l, int r, int x) {
    std::vector<int> next_candidates;
    int len = r - l + 1;

    for (int s : candidates) {
        bool s_in_range = (s >= l && s <= r);
        
        int h_response = s_in_range ? len - 1 : len;
        int d_response = s_in_range ? len : len - 1;

        int current_mask = state_masks[s];
        int next_mask = 0;
        
        // From (0,0)
        if (current_mask & (1 << 0)) { 
            if (x == h_response) next_mask |= (1 << 1); // -> (1,0)
            if (x == d_response) next_mask |= (1 << 3); // -> (0,1)
        }
        // From (1,0)
        if (current_mask & (1 << 1)) {
            if (x == h_response) next_mask |= (1 << 2); // -> (2,0)
            if (x == d_response) next_mask |= (1 << 3); // -> (0,1)
        }
        // From (2,0) -> must be dishonest
        if (current_mask & (1 << 2)) { 
            if (x == d_response) next_mask |= (1 << 3); // -> (0,1)
        }
        // From (0,1)
        if (current_mask & (1 << 3)) {
            if (x == h_response) next_mask |= (1 << 1); // -> (1,0)
            if (x == d_response) next_mask |= (1 << 4); // -> (0,2)
        }
        // From (0,2) -> must be honest
        if (current_mask & (1 << 4)) {
            if (x == h_response) next_mask |= (1 << 1); // -> (1,0)
        }

        if (next_mask != 0) {
            next_candidates.push_back(s);
            state_masks[s] = next_mask;
        }
    }
    candidates = next_candidates;
}

void solve() {
    std::cin >> n;
    candidates.resize(n);
    std::iota(candidates.begin(), candidates.end(), 1);
    state_masks.assign(n + 1, 1); // All start at state (0,0), mask bit 0

    while (candidates.size() > 2) {
        std::vector<int> h2_cand, d2_cand;
        for (int s : candidates) {
            if (state_masks[s] == (1 << 2)) { // only state (2,0) is possible
                h2_cand.push_back(s);
            } else if (state_masks[s] == (1 << 4)) { // only state (0,2) is possible
                d2_cand.push_back(s);
            }
        }
        
        int l, r;
        // Prioritize queries that give deterministic information
        if (!d2_cand.empty()) {
            l = r = d2_cand[0];
        } else if (!h2_cand.empty()) {
            l = r = h2_cand[0];
        } else {
            // Default to a binary search-style query on the range of current candidates
            int min_c = n + 1, max_c = 0;
            for(int c : candidates) {
                min_c = std::min(min_c, c);
                max_c = std::max(max_c, c);
            }
            if (min_c > max_c) { // Should not happen if candidates is not empty
                 l=1; r=1; 
            } else {
                int m = min_c + (max_c - min_c) / 2;
                l = min_c;
                r = m;
            }
        }
        
        int x = do_query(l, r);
        update(l, r, x);
    }
    
    // Announce the final candidates
    for (size_t i = 0; i < candidates.size(); ++i) {
        std::cout << "! " << candidates[i] << std::endl;
        int y;
        std::cin >> y;
        if (y == 1) {
            break;
        }
    }

    std::cout << "#" << std::endl;
}