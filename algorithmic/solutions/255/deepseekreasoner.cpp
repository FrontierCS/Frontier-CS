#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Function to perform a query based on the protocol
// Prints the query and reads the response force
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
    cin >> n;

    // We maintain a prefix list. 
    // We scan through the magnets to find the second non-demagnetized magnet (z2).
    // The scan involves querying the current prefix against the next element k.
    // Until we find z2, the prefix contains at most one non-demagnetized magnet (z1),
    // so the sum of forces in prefix is at most 1 in magnitude.
    // Thus querying against a single magnet k (magnitude at most 1) is safe (product <= 1).
    
    vector<int> prefix;
    prefix.push_back(1);
    int z2 = -1;
    
    for (int k = 2; k <= n; ++k) {
        vector<int> right = {k};
        int f = query(prefix, right);
        if (f != 0) {
            z2 = k;
            break;
        }
        prefix.push_back(k);
    }

    // Now prefix contains indices 1...z2-1.
    // We know z2 is a magnet. The interaction between prefix and z2 was non-zero.
    // This implies that the sum of types in prefix is non-zero.
    // Since we stopped at the first non-zero interaction, the prefix must contain exactly one magnet z1.
    // We find z1 using binary search.
    
    int z1 = -1;
    int low = 0, high = prefix.size() - 1;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> left_subset;
        for (int i = 0; i <= mid; ++i) {
            left_subset.push_back(prefix[i]);
        }
        vector<int> right = {z2};
        int f = query(left_subset, right);
        if (f != 0) {
            // z1 is in the left part
            high = mid;
        } else {
            // z1 is in the right part
            low = mid + 1;
        }
    }
    z1 = prefix[low];

    vector<int> demagnetized;
    // All indices in 1...z2 that are not z1 and not z2 are demagnetized.
    for (int i = 1; i < z2; ++i) {
        if (i != z1) {
            demagnetized.push_back(i);
        }
    }

    // For the remaining magnets z2+1 ... n, we can simply test each one against z1.
    // Since z1 is a magnet, interaction will be non-zero iff the tested magnet is not demagnetized.
    // This is safe because |z1| = 1 and tested magnet |t| <= 1, so product <= 1.
    if (z2 < n) {
        vector<int> tester = {z1};
        for (int k = z2 + 1; k <= n; ++k) {
            vector<int> target = {k};
            int f = query(tester, target);
            if (f == 0) {
                demagnetized.push_back(k);
            }
        }
    }

    // Output result
    cout << "! " << demagnetized.size();
    if (!demagnetized.empty()) {
        cout << " ";
        for (size_t i = 0; i < demagnetized.size(); ++i) {
            cout << demagnetized[i] << (i == demagnetized.size() - 1 ? "" : " ");
        }
    }
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}