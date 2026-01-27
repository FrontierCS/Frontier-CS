#include <iostream>
#include <vector>
#include <numeric>
#include <cstdlib>

using namespace std;

// Function to perform a query
// Prints the query in the specified format and returns the force
int query(const vector<int>& left, const vector<int>& right) {
    cout << "? " << left.size() << " " << right.size() << endl;
    for (size_t i = 0; i < left.size(); ++i) {
        cout << left[i] << (i == left.size() - 1 ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < right.size(); ++i) {
        cout << right[i] << (i == right.size() - 1 ? "" : " ");
    }
    cout << endl;
    
    int force;
    cin >> force;
    return force;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    int q_idx = -1;
    vector<int> left_set;
    
    // Step 1: Find the second magnetic magnet (q)
    // We scan with expanding left set {1...i} vs {i+1}
    // The force between a set of magnets L and R is (sum(v_L)) * (sum(v_R)).
    // Initially, sum(v_L) will be 0 until we include the first magnetic magnet.
    // Once we include the first magnetic magnet (p), sum(v_L) becomes non-zero (1 or -1).
    // Then we continue until we hit the second magnetic magnet (q) on the right side.
    // At that point, sum(v_L) is non-zero (from p) and sum(v_R) is non-zero (from q),
    // so the force will be non-zero.
    for (int i = 1; i < n; ++i) {
        left_set.push_back(i);
        vector<int> right_set = {i + 1};
        int f = query(left_set, right_set);
        if (f != 0) {
            q_idx = i + 1;
            break;
        }
    }

    // Step 2: Find the first magnetic magnet (p) in the range 1...q_idx-1
    // We know there is exactly one magnetic magnet in this range.
    // We can use binary search. Query {1...mid} vs {q_idx}.
    // Since q_idx is magnetic, the result is non-zero if and only if p is in {1...mid}.
    int l = 1, r = q_idx - 1;
    int p_idx = -1;
    
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> test_left;
        test_left.reserve(mid);
        for (int k = 1; k <= mid; ++k) test_left.push_back(k);
        vector<int> test_right = {q_idx};
        
        int f = query(test_left, test_right);
        if (f != 0) {
            // p is within 1...mid
            r = mid;
        } else {
            // p is in mid+1...r
            l = mid + 1;
        }
    }
    p_idx = l;

    // Step 3: Collect results
    // We have identified p and q as magnetic magnets.
    // Any magnet in 1...q-1 that is not p is demagnetized.
    vector<int> demagnetized;
    
    for (int i = 1; i < q_idx; ++i) {
        if (i != p_idx) {
            demagnetized.push_back(i);
        }
    }
    
    // For magnets after q, we check each one individually against p.
    // Query {p} vs {i}. If force is 0, i is demagnetized. Otherwise, i is magnetic.
    vector<int> p_vec = {p_idx};
    for (int i = q_idx + 1; i <= n; ++i) {
        vector<int> target = {i};
        int f = query(p_vec, target);
        if (f == 0) {
            demagnetized.push_back(i);
        }
    }
    
    // Output the answer
    cout << "! " << demagnetized.size();
    for (int x : demagnetized) {
        cout << " " << x;
    }
    cout << endl;
}

int main() {
    // Fast I/O is not strictly necessary for interactive problems with small N and manual flush (endl),
    // but we stick to standard cin/cout.
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}