#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // The median values we are looking for in the permutation of 1..n
    int target1 = n / 2;
    int target2 = n / 2 + 1;

    // Initialize random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Initial candidates are all indices from 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // To store indices that we have successfully eliminated
    // Eliminated elements are stored in pairs (one small, one large)
    vector<int> discarded;

    // Continue until we narrow down to 2 candidates
    while (candidates.size() > 2) {
        // Shuffle candidates to try random pairings
        shuffle(candidates.begin(), candidates.end(), rng);

        vector<int> stack;
        // Keep track of removed elements in the current pass
        vector<bool> removed(n + 1, false);
        
        for (int x : candidates) {
            if (stack.empty()) {
                stack.push_back(x);
            } else {
                int y = stack.back();
                
                // Construct the query set: all currently valid candidates excluding x and y
                // We assume x and y are a "balanced pair" (one < target1, one > target2)
                // and verify if the medians remain unchanged when they are removed.
                vector<int> q_indices;
                for (int c : candidates) {
                    if (!removed[c] && c != x && c != y) {
                        q_indices.push_back(c);
                    }
                }
                
                // The query set size must be even and >= 4.
                // q_indices size is always even because candidates.size() is even
                // and we remove an even number of elements (marked in 'removed' plus x,y).
                // If size is too small (0 or 2), we pad with previously discarded pairs.
                // Discarded pairs are known to be balanced (one small, one large), so adding them
                // back doesn't change the median values if the current set contains the targets.
                int ptr = 0;
                while (q_indices.size() < 4) {
                    if (ptr + 1 < discarded.size()) {
                        q_indices.push_back(discarded[ptr]);
                        q_indices.push_back(discarded[ptr+1]);
                        ptr += 2;
                    } else {
                        // Should not happen for n >= 6 given the logic
                        break;
                    }
                }
                
                if (q_indices.size() < 4) {
                    // Cannot form valid query (only possible if n < 6 or logic fails), keep x
                    stack.push_back(x);
                    continue;
                }

                // Perform query
                cout << "0 " << q_indices.size();
                for (int idx : q_indices) cout << " " << idx;
                cout << endl;

                int m1, m2;
                cin >> m1 >> m2;
                
                if (m1 == target1 && m2 == target2) {
                    // Removing x and y preserved the medians.
                    // This implies x and y are not the medians and are balanced.
                    removed[x] = true;
                    removed[y] = true;
                    discarded.push_back(x);
                    discarded.push_back(y);
                    stack.pop_back(); // Remove y from stack, x is not pushed
                } else {
                    // Medians changed, so x and y are likely "same side" or involve a target.
                    // Keep them.
                    stack.push_back(x);
                }
            }
        }
        
        // Update candidates list for the next round
        vector<int> new_candidates;
        for (int c : candidates) {
            if (!removed[c]) {
                new_candidates.push_back(c);
            }
        }
        candidates = new_candidates;
    }

    // Output the final answer
    cout << "1 " << candidates[0] << " " << candidates[1] << endl;

    return 0;
}