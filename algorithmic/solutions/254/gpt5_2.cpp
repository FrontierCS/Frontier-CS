#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int nn = n * n;
        int k = nn - n + 1;
        for (int i = 0; i < k; ++i) {
            if (i) cout << ' ';
            cout << (nn - i);
        }
        cout << '\n';
    }
    return 0;
}