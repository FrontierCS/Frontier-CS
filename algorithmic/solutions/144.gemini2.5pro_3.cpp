#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Function to make a query and read the response
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

// Function to find the common element between two pairs (representing sets of medians)
int get_common_median(pair<int, int> m1, pair<int, int> m2) {
    if (m1.first == m2.first || m1.first == m2.second) {
        return m1.first;
    }
    if (m1.second == m2.first || m1.second == m2.second) {
        return m1.second;
    }
    return -1; // No common median
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    // Step 1: Find the indices of the minimum (1) and maximum (n) elements.
    int cand1 = 1;
    int cand2 = 2;

    for (int i = 3; i <= n; ++i) {
        vector<int> helpers;
        for (int j = 1; j <= n; ++j) {
            if (j != cand1 && j != cand2 && j != i) {
                helpers.push_back(j);
                if (helpers.size() == 2) break;
            }
        }
        int l1 = helpers[0];
        int l2 = helpers[1];

        // Check if i is the median among {cand1, cand2, i}
        auto m1 = query({cand1, cand2, i, l1});
        auto m2 = query({cand1, cand2, i, l2});
        if (get_common_median(m1, m2) != -1) {
            // i's value is between cand1's and cand2's.
            // The extremes cand1 and cand2 remain unchanged.
            continue;
        }

        // i is an extreme, so one of cand1 or cand2 is the median.
        // Check if cand1 is the median among {cand1, cand2, i}
        m1 = query({cand2, i, cand1, l1});
        m2 = query({cand2, i, cand1, l2});
        if (get_common_median(m1, m2) != -1) {
            // cand1's value is between. cand1 is no longer an extreme candidate.
            // The new extremes are i and cand2. We replace cand1 with i.
            cand1 = i;
        } else {
            // cand2's value must be between. cand2 is no longer an extreme candidate.
            // The new extremes are i and cand1. We replace cand2 with i.
            cand2 = i;
        }
    }

    int min_idx = cand1;
    int max_idx = cand2;

    // Step 2: Determine values for all other indices
    vector<int> others;
    for (int i = 1; i <= n; ++i) {
        if (i != min_idx && i != max_idx) {
            others.push_back(i);
        }
    }

    vector<pair<int, int>> p_others;
    for (int k : others) {
        vector<int> k_helpers;
        for(int other_k : others) {
            if (k != other_k) {
                k_helpers.push_back(other_k);
                if (k_helpers.size() == 2) break;
            }
        }
        int l1 = k_helpers[0];
        int l2 = k_helpers[1];

        auto m1 = query({min_idx, max_idx, k, l1});
        auto m2 = query({min_idx, max_idx, k, l2});
        int val_k = get_common_median(m1, m2);
        p_others.push_back({val_k, k});
    }

    sort(p_others.begin(), p_others.end());

    // The full permutation's medians are n/2 and n/2+1.
    // The sorted list of all n values is 1, p_others values ..., n.
    // The (n/2)-th and (n/2+1)-th smallest values in the whole permutation
    // correspond to the (n/2-2)-th and (n/2-1)-th (0-indexed) elements
    // in our sorted p_others list.
    int med1_idx = p_others[n / 2 - 2].second;
    int med2_idx = p_others[n / 2 - 1].second;

    cout << "1 " << med1_idx << " " << med2_idx << endl;

    return 0;
}