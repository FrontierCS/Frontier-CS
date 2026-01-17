#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to handle I/O for a single test case
void solve() {
    int n;
    std::cin >> n;

    // Initially, all pens are candidates
    std::vector<int> candidates(n);
    std::iota(candidates.begin(), candidates.end(), 0);

    // Run tournament rounds until only two candidates are left
    while (candidates.size() > 2) {
        std::vector<int> next_candidates;
        
        // If there's an odd number of candidates, the last one gets a bye
        if (candidates.size() % 2 != 0) {
            next_candidates.push_back(candidates.back());
            candidates.pop_back();
        }

        // Pair up remaining candidates and determine winners
        for (size_t i = 0; i < candidates.size(); i += 2) {
            int u = candidates[i];
            int v = candidates[i + 1];

            // Query pen u
            std::cout << "0 " << u << std::endl;
            int r_u;
            std::cin >> r_u;

            // Query pen v
            std::cout << "0 " << v << std::endl;
            int r_v;
            std::cin >> r_v;

            // The winner is the one that has ink.
            // If both have ink, we arbitrarily choose u.
            // If u is empty, v wins by default.
            if (r_u == 1) {
                next_candidates.push_back(u);
            } else {
                next_candidates.push_back(v);
            }
        }
        candidates = next_candidates;
    }

    // Output the final two candidates
    std::cout << "1 " << candidates[0] << " " << candidates[1] << std::endl;
}

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