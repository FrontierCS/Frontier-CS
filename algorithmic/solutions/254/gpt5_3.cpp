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
        long long total = 1LL * n * n;
        long long k = total - n + 1;
        cout << "!";
        for (long long i = 1; i <= k; i++) {
            cout << " " << i;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}