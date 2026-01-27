#include <iostream>
#include <vector>

using namespace std;

// Function to perform a query to the interactive machine
// l: vector of indices for magnets on the left
// r: vector of indices for magnets on the right
int query(const vector<int>& l, const vector<int>& r) {
    cout << "? " << l.size() << " " << r.size() << endl;
    for (size_t i = 0; i < l.size(); ++i) {
        cout << l[i] << (i + 1 == l.size() ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < r.size(); ++i) {
        cout << r[i] << (i + 1 == r.size() ? "" : " ");
    }
    cout << endl;
    
    int force;
    cin >> force;
    return force;
}

void solve() {
    int n;
    cin >> n;

    // Step 1: Find the second non-zero magnet.
    // We incrementally build a prefix set on the left side and test it against the next magnet on the right side.
    // Initially, the sum of values (force potential) of magnets in the prefix is 0 (since they are all demagnetized).
    // Once we add the first non-zero magnet to the prefix, the sum becomes 1 or -1.
    // Since we only proceed one by one, the sum on the left never exceeds magnitude 1 before we detect the second non-zero magnet.
    // When we query the prefix (sum +/- 1) against the next magnet (value +/- 1), the force will be +/- 1.
    // The machine only crashes if |force| > 1, which we avoid.
    
    vector<int> prefix;
    prefix.reserve(n);
    prefix.push_back(1);
    
    int second_nonzero = -1;
    
    for (int i = 2; i <= n; ++i) {
        vector<int> current = {i};
        int f = query(prefix, current);
        
        if (f != 0) {
            second_nonzero = i;
            break;
        }
        
        prefix.push_back(i);
    }
    
    // Step 2: Find the first non-zero magnet within the identified prefix.
    // The 'prefix' vector contains indices 1 to (second_nonzero - 1).
    // We know exactly one of these is non-zero, and all prior interactions resulted in 0.
    // We can use binary search on 'prefix', verifying subsets against 'second_nonzero'.
    
    int l = 0, r = prefix.size() - 1;
    int first_nonzero_idx = -1; // Index relative to the 'prefix' vector
    
    while (l < r) {
        int mid = (l + r) / 2;
        
        vector<int> test_subset;
        test_subset.reserve(mid - l + 1);
        for (int k = l; k <= mid; ++k) {
            test_subset.push_back(prefix[k]);
        }
        
        int f = query(test_subset, {second_nonzero});
        
        if (f != 0) {
            // The non-zero magnet is in the left half [l, mid]
            r = mid;
        } else {
            // The non-zero magnet is in the right half [mid + 1, r]
            l = mid + 1;
        }
    }
    first_nonzero_idx = l;
    int first_nonzero = prefix[first_nonzero_idx];
    
    // Step 3: Identify all demagnetized magnets.
    vector<int> demagnetized;
    demagnetized.reserve(n);
    
    // All magnets in the prefix except 'first_nonzero' are demagnetized.
    for (int x : prefix) {
        if (x != first_nonzero) {
            demagnetized.push_back(x);
        }
    }
    
    // For the remaining magnets (indices > second_nonzero), we must test them.
    // We can use 'first_nonzero' (which is definitely N or S) as a probe.
    // A query of {first_nonzero} vs {i} will yield 0 if i is demagnetized, and non-zero otherwise.
    for (int i = second_nonzero + 1; i <= n; ++i) {
        int f = query({first_nonzero}, {i});
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
    // Optimization for I/O operations, though standard flush via endl is used.
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