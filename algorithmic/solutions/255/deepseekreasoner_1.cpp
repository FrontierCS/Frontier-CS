#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Function to perform a query according to protocol
// Flushes output automatically via endl
int query(const vector<int>& l, const vector<int>& r) {
    cout << "? " << l.size() << " " << r.size() << "\n";
    for(size_t i = 0; i < l.size(); ++i) {
        cout << l[i] << (i + 1 == l.size() ? "" : " ");
    }
    cout << "\n";
    for(size_t i = 0; i < r.size(); ++i) {
        cout << r[i] << (i + 1 == r.size() ? "" : " ");
    }
    cout << endl;
    
    int res;
    cin >> res;
    // -2 usually indicates an invalid state or crash in interactive problems
    if (res == -2) exit(0); 
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    // Phase 1: Find the second non-zero magnet.
    // We scan i from 2 to n. We query the cumulative set {1...i-1} against {i}.
    // Until we find the second non-zero magnet, the prefix sum on the left is always 0 or +/- 1.
    // This ensures we never crash the machine (|force| <= 1).
    // When we find a non-zero force, 'i' is the second non-zero magnet, and the first one is in 1..i-1.
    int idx = -1;
    for(int i = 2; i <= n; ++i) {
        vector<int> left;
        left.reserve(i - 1);
        for(int k = 1; k < i; ++k) left.push_back(k);
        vector<int> right = {i};
        
        int f = query(left, right);
        if(f != 0) {
            idx = i;
            break;
        }
    }

    // Phase 2: Find the first non-zero magnet (pos) in range [1, idx-1].
    // Since we know 'idx' is non-zero, we use it as a probe.
    // We binary search for the index 'pos' where the prefix sum becomes non-zero.
    // Query {1..mid} vs {idx}. If force != 0, it means sum(1..mid) != 0, so pos <= mid.
    int pos = -1;
    int l = 1, r = idx - 1;
    while(l <= r) {
        int mid = (l + r) / 2;
        vector<int> left;
        left.reserve(mid);
        for(int k = 1; k <= mid; ++k) left.push_back(k);
        vector<int> right = {idx};
        
        int f = query(left, right);
        if(f != 0) {
            pos = mid;
            r = mid - 1;
        } else {
            l = mid + 1;
        }
    }

    // Phase 3: Identify all zero magnets.
    // We know 'pos' and 'idx' are non-zero magnets.
    // Based on our logic:
    // 1. All magnets before 'pos' must be zero (otherwise sum would be non-zero earlier).
    // 2. All magnets between 'pos' and 'idx' must be zero (otherwise force would trigger earlier in Phase 1).
    // 3. For magnets after 'idx', we test them individually against 'pos'.
    
    vector<int> ans;
    for(int i = 1; i < pos; ++i) ans.push_back(i);
    for(int i = pos + 1; i < idx; ++i) ans.push_back(i);
    
    for(int i = idx + 1; i <= n; ++i) {
        vector<int> left = {pos};
        vector<int> right = {i};
        int f = query(left, right);
        if(f == 0) {
            ans.push_back(i);
        }
    }

    cout << "! " << ans.size();
    for(int x : ans) cout << " " << x;
    cout << endl;
}

int main() {
    // Optimize standard streams but maintain synchronization manually if needed (endl flushes)
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if(cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}