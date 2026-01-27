#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Helper function to interact with the interactor
// Returns the force measured by the machine
int ask(const vector<int>& left, const vector<int>& right) {
    cout << "? " << left.size() << " " << right.size() << endl;
    for (size_t i = 0; i < left.size(); ++i) {
        cout << left[i] << (i == left.size() - 1 ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < right.size(); ++i) {
        cout << right[i] << (i == right.size() - 1 ? "" : " ");
    }
    cout << endl;
    
    int response;
    if (!(cin >> response)) {
        exit(0);
    }
    // If response is -2, it typically signifies invalid query or crash in some interactive problems,
    // though usually the program just terminates.
    if (response == -2) exit(0); 
    return response;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    // Phase 1: Linear Scan to find the second non-zero magnet.
    // We effectively search for the first prefix that has a non-zero interaction with the next element.
    // Let p1 be the index of the first non-zero magnet, and p2 be the second.
    // For any i < p2 - 1, the query({1...i}, {i+1}) will return 0 because:
    // - If i < p1, sum(1...i) is 0.
    // - If p1 <= i < p2-1, sum(1...i) is +/- 1 (due to p1), but magnet i+1 is 0.
    // When we reach i = p2 - 1, sum(1...i) is +/- 1 and magnet i+1 (which is p2) is +/- 1.
    // The force will be +/- 1. We stop here.
    
    vector<int> left_set;
    left_set.push_back(1);
    
    int second_nz = -1;
    
    for (int i = 2; i <= n; ++i) {
        // We test the accumulated prefix against the new element `i`
        // Using exactly 1 element on the right is crucial to efficiently check while staying safe (|F| <= 1).
        int res = ask(left_set, {i});
        if (res != 0) {
            second_nz = i;
            break;
        }
        left_set.push_back(i);
    }
    
    if (second_nz == -1) {
        // This case should not be reachable given the problem constraints (at least 2 non-zero magnets).
        return;
    }
    
    // left_set contains {1, 2, ..., second_nz - 1}.
    // There is exactly one non-zero magnet in left_set (which is p1).
    // The accumulated query result being non-zero confirms p1 is in left_set.
    
    // Phase 2: Binary Search to detect p1 within left_set.
    // Since only one magnet in left_set is non-zero, any subset sum containing it will be +/- 1.
    // We can test ranges [0, mid] of left_set against the known non-zero magnet `second_nz`.
    
    int p1 = -1;
    int l = 0, r = left_set.size() - 1;
    
    while (l < r) {
        int mid = l + (r - l) / 2;
        vector<int> subset;
        for (int k = 0; k <= mid; ++k) subset.push_back(left_set[k]);
        
        // Query subset of potential p1 candidates against the known non-zero p2
        int res = ask(subset, {second_nz});
        if (res != 0) {
            // p1 is in the first half (subset includes p1)
            r = mid;
        } else {
            // p1 is in the second half
            l = mid + 1;
        }
    }
    p1 = left_set[l];
    
    // Phase 3: Identify all demagnetized magnets.
    vector<int> demagnetized;
    
    // 1. All elements in left_set except p1 are demagnetized
    for (int x : left_set) {
        if (x != p1) demagnetized.push_back(x);
    }
    
    // 2. Check remaining magnets (from second_nz + 1 to n)
    // We can test each remaining magnet against `second_nz` (which we know is charged).
    // If force is 0, the magnet is demagnetized.
    for (int i = second_nz + 1; i <= n; ++i) {
        int res = ask({second_nz}, {i});
        if (res == 0) {
            demagnetized.push_back(i);
        }
    }
    
    // Output result
    cout << "! " << demagnetized.size();
    for (int x : demagnetized) {
        cout << " " << x;
    }
    cout << endl;
}

int main() {
    // Interactive problems usually require manual flushing, which endl does.
    // Sync with stdio can be left on.
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}