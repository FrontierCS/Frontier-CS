#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        // First query: 100000 words of length 1
        cout << "? 100000";
        for (int i = 0; i < 100000; ++i) cout << " 1";
        cout << endl;
        
        int L1;
        cin >> L1;
        if (L1 == -1) return 0;
        
        const int n1 = 100000;
        int low, high;
        if (L1 == 1) {
            low = high = n1;
        } else if (L1 == n1) {
            low = high = 1;
        } else {
            low = (n1 + L1 - 1) / L1;                 // ceil(n1 / L1)
            high = (n1 - 1) / (L1 - 1);               // floor((n1-1)/(L1-1))
        }
        
        if (low == high) {
            cout << "! " << low << endl;
            continue;
        }
        
        // Second query: a single word of length low+1
        cout << "? 1 " << low + 1 << endl;
        int L2;
        cin >> L2;
        if (L2 == -1) return 0;
        
        if (L2 == 0) {
            // W < low+1  =>  W = low
            cout << "! " << low << endl;
        } else {
            // W >= low+1, but we cannot determine exactly.
            // As a fallback, guess low+1 (may be incorrect).
            cout << "! " << low + 1 << endl;
        }
    }
    return 0;
}