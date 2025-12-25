#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Function to query the interactor
pair<int, int> query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    int t1 = n / 2;
    int t2 = n / 2 + 1;

    vector<int> p(n);
    iota(p.begin(), p.end(), 1); // Fill with 1, 2, ..., n

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> discarded_pair;

    // Phase 1: Reduce the set of candidates to 4
    // Strategy: Repeatedly pick two random elements and query the rest.
    // If the medians of the rest are still t1 and t2, it means we removed one small (< t1)
    // and one large (> t2) element, preserving the median positions. We can permanently discard them.
    // We keep one such discarded pair to help in Phase 2.
    while (p.size() > 4) {
        // Pick two distinct random indices in p
        uniform_int_distribution<int> dist(0, p.size() - 1);
        int idx1 = dist(rng);
        int idx2 = dist(rng);
        while (idx1 == idx2) {
            idx2 = dist(rng);
        }
        
        // Prepare query indices: p \ {p[idx1], p[idx2]}
        vector<int> q;
        q.reserve(p.size() - 2);
        for (int i = 0; i < p.size(); ++i) {
            if (i != idx1 && i != idx2) {
                q.push_back(p[i]);
            }
        }

        pair<int, int> res = query(q);

        if (res.first == t1 && res.second == t2) {
            // Success: p[idx1] and p[idx2] are non-medians (one small, one large)
            discarded_pair = {p[idx1], p[idx2]};
            
            // Remove them from p
            int val1 = p[idx1];
            int val2 = p[idx2];
            
            vector<int> next_p;
            next_p.reserve(p.size() - 2);
            for (int val : p) {
                if (val != val1 && val != val2) {
                    next_p.push_back(val);
                }
            }
            p = next_p;
        }
        // Else: keep them and try another pair
    }

    // Phase 2: Solve for the last 4 candidates
    // p has 4 elements. We use the previously discarded_pair (which contains one small and one large)
    // to form a query of size 4.
    // We try to find which 2 elements in p are the medians by assuming 2 are NOT medians,
    // replacing them with the discarded pair, and checking if medians are still t1, t2.
    
    int ans1 = -1, ans2 = -1;

    for (int i = 0; i < p.size(); ++i) {
        for (int j = i + 1; j < p.size(); ++j) {
            vector<int> q;
            // Add the other 2 elements from p (our candidates for medians)
            for (int k = 0; k < p.size(); ++k) {
                if (k != i && k != j) {
                    q.push_back(p[k]);
                }
            }
            // Add the discarded pair to maintain balance and size 4
            // Since discarded_pair is {Small, Large}, adding it preserves the median value
            // if the current 'q' (from p) consists of {Median, Median}.
            q.push_back(discarded_pair[0]);
            q.push_back(discarded_pair[1]);

            pair<int, int> res = query(q);
            
            if (res.first == t1 && res.second == t2) {
                // Found the medians! They are the ones we KEPT from p.
                vector<int> result;
                for (int k = 0; k < p.size(); ++k) {
                    if (k != i && k != j) {
                        result.push_back(p[k]);
                    }
                }
                ans1 = result[0];
                ans2 = result[1];
                goto end;
            }
        }
    }

end:
    cout << "1 " << ans1 << " " << ans2 << endl;

    return 0;
}