#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to perform query operation
// Returns the number of value-contiguous segments in p[l...r]
int query(int l, int r) {
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

// Function to perform swap operation
void perform_swap(int i, int j) {
    cout << "2 " << i << " " << j << endl;
    int res;
    cin >> res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, l1, l2;
    if (!(cin >> n >> l1 >> l2)) return 0;

    // Base case for n=1
    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }

    vector<pair<int, int>> history;

    // Helper lambda to perform swap and record it
    auto do_swap = [&](int i, int j) {
        if (i == j) return;
        perform_swap(i, j);
        history.push_back({i, j});
    };

    // Step 1: Find an extreme value (1 or n) and ensure it is at p[1].
    // An element is extreme if the remaining elements form 1 segment (since 1..n is 1 segment).
    // Specifically, if p[1] is 1 or n, then p[2...n] contains 2...n or 1...n-1, which forms 1 segment.
    // If p[1] is not extreme (say k where 1 < k < n), p[2...n] lacks k, splitting 1...n into two parts: 1..k-1 and k+1..n.
    // Thus p[2...n] would have 2 segments.
    
    // Check if initial p[1] is extreme
    bool found = false;
    if (query(2, n) == 1) {
        found = true;
    } else {
        // Try bringing other elements to position 1
        for (int i = 2; i <= n; ++i) {
            do_swap(1, i);
            if (query(2, n) == 1) {
                found = true;
                break;
            }
        }
    }

    // Step 2: Greedily build the sequence.
    // We assume p[1] is '1' (or 'n', indistinguishable).
    // We want to place '2' at p[2], '3' at p[3], etc.
    // Invariant: p[1]...p[k-1] are contiguous values.
    // We look for p[k] such that it connects to p[1]...p[k-1].
    // If p[k] connects, then adding it to the set doesn't increase segment count relative to adding an isolated element.
    // Specifically:
    // Query([1, m]) counts segments in {p[1]..p[k-1]} U {p[k]..p[m]}.
    // Query([k, m]) counts segments in {p[k]..p[m]}.
    // If target is in {p[k]..p[m]}, it bridges the block {p[1]..p[k-1]} with its component in {p[k]..p[m]}.
    // So Query([1, m]) == Query([k, m]).
    // If target is NOT in {p[k]..p[m]}, {p[1]..p[k-1]} is isolated.
    // So Query([1, m]) == Query([k, m]) + 1.
    
    for (int k = 2; k < n; ++k) {
        // Quick check if p[k] is already the correct element
        if (query(1, k) == 1) {
            continue;
        }

        // Binary search to find the position of the next element
        int low = k + 1, high = n;
        int target_idx = -1;

        while (low <= high) {
            int mid = low + (high - low) / 2;
            int q_combined = query(1, mid);
            int q_part = query(k, mid);
            
            if (q_combined == q_part) {
                // Found in [k, mid] (actually [k+1, mid] since p[k] checked)
                target_idx = mid;
                high = mid - 1;
            } else {
                // Not in [k, mid]
                low = mid + 1;
            }
        }
        
        if (target_idx != -1) {
            do_swap(k, target_idx);
        }
    }

    // Step 3: Reconstruct the original permutation
    // Start with the sorted state [1, 2, ..., n]
    vector<int> p(n + 1);
    iota(p.begin(), p.end(), 0);

    // Apply swaps in reverse order to get the initial state
    for (int i = history.size() - 1; i >= 0; --i) {
        swap(p[history[i].first], p[history[i].second]);
    }

    // Output result
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}