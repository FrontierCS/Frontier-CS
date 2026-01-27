#include <iostream>
#include <vector>

using namespace std;

void solve() {
    int n;
    if (!(cin >> n)) return;

    int q = -1;
    // We look for the first index 'q' such that v[q] != 0 and the prefix sum up to q-1 is non-zero.
    // The query ? {1..i} {i+1} calculates sum(1..i) * v[i+1].
    // Initially, sum is 0. Once we include the first non-zero magnet (let's call it p), the sum becomes +/-1.
    // It stays +/-1 until we include another non-zero magnet or encounter a cancellation.
    // However, if we encounter a second non-zero magnet at index q, the query {1..q-1} vs {q} will return +/-1 * v[q] which is non-zero.
    // Thus, this loop finds the second non-zero magnet 'q'.
    for (int i = 1; i < n; ++i) {
        cout << "? " << i << " " << 1 << endl;
        for (int j = 1; j <= i; ++j) {
            cout << j << (j == i ? "" : " ");
        }
        cout << endl;
        cout << i + 1 << endl;

        int f;
        cin >> f;
        if (f != 0) {
            q = i + 1;
            break;
        }
    }

    // Now we know q is non-zero.
    // We also know that in the range 1..q-1, there is exactly one non-zero magnet 'p' 
    // (otherwise the sum would have been zero or we would have stopped earlier).
    // We find 'p' using binary search by querying subsets of 1..q-1 against q.
    int p = -1;
    int low = 1, high = q - 1;
    while (low < high) {
        int mid = (low + high) / 2;
        int len = mid - low + 1;
        cout << "? " << len << " " << 1 << endl;
        for (int j = low; j <= mid; ++j) {
            cout << j << (j == mid ? "" : " ");
        }
        cout << endl;
        cout << q << endl;

        int f;
        cin >> f;
        if (f != 0) {
            // The non-zero magnet is in the checked range
            high = mid;
        } else {
            // The non-zero magnet is in the other half
            low = mid + 1;
        }
    }
    p = low;

    vector<int> ans;
    // All indices in 1..q-1 except p are demagnetized
    for (int i = 1; i < q; ++i) {
        if (i != p) ans.push_back(i);
    }

    // For indices > q, we can check them individually against q.
    // Since v[q] != 0, the force will be 0 iff the other magnet is demagnetized.
    for (int i = q + 1; i <= n; ++i) {
        cout << "? 1 1" << endl;
        cout << q << endl;
        cout << i << endl;
        
        int f;
        cin >> f;
        if (f == 0) ans.push_back(i);
    }

    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}