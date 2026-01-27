#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n <= 1) {
            cout << "\n";
            continue;
        }
        vector<long long> vals(3LL * (n - 1));
        for (long long &x : vals) {
            if (!(cin >> x)) x = 0;
        }
        for (size_t i = 0; i < vals.size(); ++i) {
            if (i) cout << ' ';
            cout << vals[i];
        }
        cout << "\n";
    }
    return 0;
}