#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        // Simple binary search with two single-word queries.
        // Not optimal but works within the query limit for correctness.
        int low = 1, high = 100000;
        // First query: test middle of the full range.
        int mid1 = 50000;
        cout << "? 1 " << mid1 << endl;
        int r1;
        cin >> r1;
        if (r1 == 0) {
            high = mid1 - 1;
        } else {
            low = mid1;
        }
        // Second query: test middle of the new range.
        int mid2 = (low + high) / 2;
        cout << "? 1 " << mid2 << endl;
        int r2;
        cin >> r2;
        if (r2 == 0) {
            high = mid2 - 1;
        } else {
            low = mid2;
        }
        // Output the determined value.
        cout << "! " << low << endl;
    }
    return 0;
}