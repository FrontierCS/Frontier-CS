#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        // Output any derangement: simple cyclic shift by 1
        for (int i = 1; i <= n; ++i) {
            int val = (i % n) + 1;
            if (i > 1) cout << ' ';
            cout << val;
        }
        if (t) cout << '\n';
    }
    return 0;
}