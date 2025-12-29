#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    for (long long i = 0; i < 2 * n; ++i) {
        if (i) cout << ' ';
        cout << 0;
    }
    cout << '\n';
    return 0;
}