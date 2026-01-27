#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Function to perform a query based on the problem statement.
// It prints the query in the required format and reads the force value.
int query(const vector<int>& left, const vector<int>& right) {
    cout << "? " << left.size() << " " << right.size() << endl;
    for (size_t i = 0; i < left.size(); ++i) {
        cout << left[i] << (i + 1 == left.size() ? "" : " ");
    }
    cout << endl;
    for (size_t i = 0; i < right.size(); ++i) {
        cout << right[i] << (i + 1 == right.size() ? "" : " ");
    }
    cout << endl;
    
    int f;
    // If input reading fails (e.g. machine crashed or wrong format), terminate.
    if (!(cin >> f)) exit(0);
    return f;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    int k = -1;
    // Step 1: Find the second non-zero magnet (index k).
    // We accumulate magnets 1..i-1 on the left and test against i on the right.
    // The accumulated sum of 1..i-1 stays 0 (all zeros) until we include the first non-zero magnet p.
    // Once p is included, the sum becomes +/-1 (since only p is non-zero in the prefix).
    // We won't get a non-zero force until we test against another non-zero magnet.
    // Thus, the first i for which the force is non-zero is the second non-zero magnet k.
    for (int i = 2; i <= n; ++i) {
        vector<int> left;
        left.reserve(i - 1);
        for (int j = 1; j < i; ++j) left.push_back(j);
        
        // Pass temporary vector {i} for the right side
        if (query(left, {i}) != 0) {
            k = i;
            break;
        }
    }

    // Step 2: Find the first non-zero magnet p within 1..k-1.
    // We know that for the prefix 1..x, the sum is non-zero if and only if x >= p.
    // We can use binary search to find p.
    // In each step, we query 1..mid against k. Since k is known non-zero,
    // a non-zero force implies the prefix sum is non-zero, so p <= mid.
    int l = 1, r = k - 1;
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> left;
        left.reserve(mid);
        for (int j = 1; j <= mid; ++j) left.push_back(j);
        
        if (query(left, {k}) != 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    int p = l;

    vector<int> ans;
    // All magnets in 1..k-1 are zeros except p.
    for (int i = 1; i < k; ++i) {
        if (i != p) ans.push_back(i);
    }
    
    // Step 3: Identify magnets in k+1..n.
    // We test each magnet i against the known non-zero magnet k.
    // If force is 0, i is zero. Else i is non-zero.
    for (int i = k + 1; i <= n; ++i) {
        if (query({k}, {i}) == 0) {
            ans.push_back(i);
        }
    }

    // Output the answer
    cout << "! " << ans.size();
    for (int x : ans) {
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