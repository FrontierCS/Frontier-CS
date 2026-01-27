#include <iostream>
#include <vector>

using namespace std;

// Function to perform a query
// l and r contain indices of magnets (1-based)
int query(const vector<int>& l, const vector<int>& r) {
    cout << "? " << l.size() << " " << r.size() << endl;
    for (size_t i = 0; i < l.size(); ++i) {
        cout << l[i] << (i == l.size() - 1 ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < r.size(); ++i) {
        cout << r[i] << (i == r.size() - 1 ? "" : " ");
    }
    cout << endl;
    
    int f;
    cin >> f;
    return f;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    int q = -1;
    vector<int> l_vec;
    l_vec.push_back(1);
    
    // Scan to find the second charged magnet q
    // By growing l_vec, we ensure that as soon as we have one charged magnet in l_vec (at index p)
    // and we encounter the next charged magnet as 'i', the force becomes non-zero.
    // l_vec will never contain more than 1 charged magnet during this process before we break,
    // so we avoid crashing the machine (sum is never >= 2 or <= -2).
    for (int i = 2; i <= n; ++i) {
        vector<int> r_vec = {i};
        int f = query(l_vec, r_vec);
        if (f != 0) {
            q = i;
            break;
        }
        l_vec.push_back(i);
    }
    
    // At this point, l_vec is {1, ..., q-1} and contains exactly one charged magnet.
    // q is the second charged magnet found.
    // We now binary search for the first charged magnet p in range [1, q-1].
    // Since p is the ONLY charged magnet in [1, q-1], any prefix sum including p will be non-zero (1 or -1).
    
    int p = -1;
    int low = 1, high = q - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        
        // Construct left set {1, ..., mid}
        vector<int> l_bs;
        l_bs.reserve(mid);
        for (int k = 1; k <= mid; ++k) l_bs.push_back(k);
        vector<int> r_bs = {q};
        
        // If force is non-zero, then the charged magnet is in {1, ..., mid}
        if (query(l_bs, r_bs) != 0) {
            p = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // Collect results
    vector<int> empty_magnets;
    
    // We know p and q are charged.
    // Before p, all are empty.
    for (int i = 1; i < p; ++i) empty_magnets.push_back(i);
    // Between p and q, all are empty.
    for (int i = p + 1; i < q; ++i) empty_magnets.push_back(i);

    // Check magnets after q using p as a probe
    // Since we check 1 vs 1, force is at most 1, so it's safe.
    for (int i = q + 1; i <= n; ++i) {
        vector<int> l_chk = {p};
        vector<int> r_chk = {i};
        if (query(l_chk, r_chk) == 0) {
            empty_magnets.push_back(i);
        }
    }

    // Output result
    cout << "! " << empty_magnets.size();
    for (int x : empty_magnets) cout << " " << x;
    cout << endl;
}

int main() {
    // No sync_with_stdio(false) to ensure safety with interactive IO
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}