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

    int target1 = n / 2;
    int target2 = n / 2 + 1;

    // Candidates initially contains all indices 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // To store a pair {small, large} that we have successfully discarded
    // This is needed for padding when we reach k=4 candidates
    vector<int> last_discarded_pair;

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // We continue until we have identified the two medians
    // The loop handles reducing candidates size until we find the answer
    while (candidates.size() > 2) {
        // Pick two distinct indices from candidates at random
        vector<int> p(candidates.size());
        iota(p.begin(), p.end(), 0);
        shuffle(p.begin(), p.end(), rng);

        int idx1 = p[0];
        int idx2 = p[1];
        
        // These are the values (original indices in permutation) we are tentatively removing/testing
        int val1 = candidates[idx1];
        int val2 = candidates[idx2];

        vector<int> query;
        if (candidates.size() > 4) {
            // Strategy: Try to remove two elements.
            // If the two removed elements are one Small (< n/2) and one Large (> n/2+1),
            // the medians of the remaining set will remain n/2 and n/2+1.
            // We query all candidates except the two chosen.
            for (size_t i = 0; i < candidates.size(); ++i) {
                if ((int)i == idx1 || (int)i == idx2) continue;
                query.push_back(candidates[i]);
            }
        } else {
            // candidates.size() == 4
            // We cannot query a subsequence of length 2 (since k >= 4).
            // We use a previously discarded pair (which we know is one Small, one Large) to pad the query to length 4.
            // If the remaining 2 candidates (kept in query) are the Medians,
            // then {Median1, Median2, Pad_Small, Pad_Large} will have medians Median1 and Median2.
            
            // Add the kept candidates
            for (size_t i = 0; i < candidates.size(); ++i) {
                if ((int)i == idx1 || (int)i == idx2) continue;
                query.push_back(candidates[i]);
            }
            // Add padding
            query.push_back(last_discarded_pair[0]);
            query.push_back(last_discarded_pair[1]);
        }

        // Print query
        cout << "0 " << query.size();
        for (int x : query) cout << " " << x;
        cout << endl;

        // Read response
        int m1, m2;
        cin >> m1 >> m2;

        if (m1 == target1 && m2 == target2) {
            // Success condition: the medians are preserved
            if (candidates.size() > 4) {
                // We found a (Small, Large) pair to discard
                last_discarded_pair = {val1, val2};
                
                // Update candidates by permanently removing val1 and val2
                vector<int> next_candidates;
                for (size_t i = 0; i < candidates.size(); ++i) {
                    if ((int)i == idx1 || (int)i == idx2) continue;
                    next_candidates.push_back(candidates[i]);
                }
                candidates = next_candidates;
            } else {
                // candidates.size() == 4
                // We kept the true Medians in the query (along with padding)
                // So the candidates we DIDN'T remove (the ones in the query from candidates) are the answer
                vector<int> ans;
                for (size_t i = 0; i < candidates.size(); ++i) {
                    if ((int)i == idx1 || (int)i == idx2) continue;
                    ans.push_back(candidates[i]);
                }
                cout << "1 " << ans[0] << " " << ans[1] << endl;
                return 0;
            }
        } else {
            // Failure: the pair we picked was not (Small, Large) or (for size 4) we removed a Median
            // Do nothing, just loop again to pick a different random pair
        }
    }

    return 0;
}