#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        if(!(cin >> n)) break;
        // Output any permutation (non-interactive placeholder)
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
    }
    return 0;
}