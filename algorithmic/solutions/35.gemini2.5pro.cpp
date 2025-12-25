#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <iterator>

using namespace std;

// Asks a query for a given value x and a set of indices S.
// To avoid copying large vectors, this version takes iterators.
bool ask_iter(int x, vector<int>::const_iterator begin, vector<int>::const_iterator end) {
    size_t sz = distance(begin, end);
    if (sz == 0) {
        return false;
    }
    cout << "? " << x << " " << sz;
    for (auto it = begin; it != end; ++it) {
        cout << " " << *it;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

// Finds the first occurrence of value x in a sorted list of available indices.
// It performs a binary search on the indices.
int find_first_occurrence(int x, const vector<int>& indices) {
    if (indices.empty()) {
        return -1;
    }

    int low = 0, high = indices.size() - 1;
    int ans_idx = -1;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        // Query if x is present in the prefix of available indices.
        if (ask_iter(x, indices.begin(), indices.begin() + mid + 1)) {
            ans_idx = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    if (ans_idx == -1) {
        return -1;
    }
    return indices[ans_idx];
}

void solve() {
    int n;
    cin >> n;

    // `used` array tracks which indices have been paired up.
    vector<bool> used(2 * n, false);
    
    // Iterate through all possible values from 1 to n.
    for (int x = 1; x <= n; ++x) {
        // Collect all indices that are not yet part of a pair.
        vector<int> current_unfound;
        current_unfound.reserve(2 * n - 1);
        for (int i = 1; i < 2 * n; ++i) {
            if (!used[i]) {
                current_unfound.push_back(i);
            }
        }

        // Find the first occurrence of x among the unfound indices.
        int pos1 = find_first_occurrence(x, current_unfound);

        if (pos1 != -1) {
            // If an occurrence is found, mark its index as used.
            used[pos1] = true;
            
            // Rebuild the list of unfound indices, now without pos1.
            vector<int> next_unfound;
            next_unfound.reserve(2 * n - 2);
            for (int i = 1; i < 2 * n; ++i) {
                if (!used[i]) {
                    next_unfound.push_back(i);
                }
            }
            
            // Look for a second occurrence.
            int pos2 = find_first_occurrence(x, next_unfound);

            if (pos2 != -1) {
                // If a second occurrence is found, mark it as used.
                used[pos2] = true;
            } else {
                // If no second occurrence is found, x must be the unique number.
                cout << "! " << x << endl;
                return;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}