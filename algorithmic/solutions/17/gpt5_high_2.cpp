#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<int> a(n);
        for (int i = 0; i < n; ++i) cin >> a[i];
        int pos = -1;
        for (int i = 0; i < n; ++i) {
            if (a[i] == n) { pos = i + 1; break; }
        }
        cout << pos << "\n";
    }
    return 0;
}