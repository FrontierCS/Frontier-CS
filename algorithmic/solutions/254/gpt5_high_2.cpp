#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        long long n;
        cin >> n;
        long long total = n * n;
        long long m = total - n + 1;
        cout << "! ";
        for (long long i = total; i >= n; --i) {
            cout << i;
            if (i != n) cout << ' ';
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}