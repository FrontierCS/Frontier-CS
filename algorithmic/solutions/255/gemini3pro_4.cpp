#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to handle interaction with the interactor
// Returns the force measured by the machine
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

    // Phase 1: Find the index `q` of the second non-zero magnet.
    // We scan i from 2 to n and query {i} against all previous magnets {1...i-1}.
    // The force will be 0 until we encounter the second non-zero magnet.
    // Explanation:
    // - Before the first non-zero magnet p, all prefix sums are 0. Force is 0.
    // - At p, prefix sum is 0 (from 1..p-1). Force is 0.
    // - After p and before q, the prefix sum is v_p (+/- 1). The current magnet i is 0. Force is 0 * v_p = 0.
    // - At q, prefix sum is v_p. Current magnet q is non-zero. Force is v_q * v_p = +/- 1.
    // This guarantees we never crash the machine (|force| <= 1).
    
    int q = -1;
    vector<int> prefix;
    prefix.push_back(1);
    
    for (int i = 2; i <= n; ++i) {
        int f = query({i}, prefix);
        if (f != 0) {
            q = i;
            break;
        }
        prefix.push_back(i);
    }
    
    // We are guaranteed to find q because there are at least 2 non-zero magnets.
    // prefix now contains 1, 2, ..., q-1. Exactly one of them is p (the first non-zero).
    
    // Phase 2: Binary search to find p in 1...q-1 using q as the probe.
    int l = 0;
    int r = prefix.size() - 1;
    
    while (l < r) {
        int mid = l + (r - l) / 2;
        vector<int> subset;
        for (int k = l; k <= mid; ++k) {
            subset.push_back(prefix[k]);
        }
        
        // Check if p is in the left half [l, mid]
        // Since q is non-zero, force is non-zero iff sum(subset) is non-zero iff p is in subset.
        int f = query({q}, subset);
        
        if (f != 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    
    int p = prefix[l];
    
    // Collect the results
    vector<int> demagnetized;
    
    // All in 1...q-1 except p are demagnetized
    for (int x : prefix) {
        if (x != p) {
            demagnetized.push_back(x);
        }
    }
    
    // Phase 3: Check magnets q+1...n individually against q
    for (int k = q + 1; k <= n; ++k) {
        int f = query({q}, {k});
        if (f == 0) {
            demagnetized.push_back(k);
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
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}