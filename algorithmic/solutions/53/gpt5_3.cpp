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
        for (int i = 1; i <= n; ++i) {
            int val = (i % n) + 1;
            cout << val << (i == n ? '\n' : ' ');
        }
    }
    return 0;
}