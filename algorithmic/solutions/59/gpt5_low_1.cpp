#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> vals;
    long long x;
    while (cin >> x) vals.push_back(x);
    if (vals.empty()) return 0;
    long long n = vals[0];
    // If only n provided, output 1..n
    if ((long long)vals.size() == 1) {
        for (long long i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
        return 0;
    }
    // If n followed by n numbers, output them
    if ((long long)vals.size() >= n + 1) {
        for (long long i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << vals[i];
        }
        cout << '\n';
        return 0;
    }
    // Fallback: print 1..n
    for (long long i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << i;
    }
    cout << '\n';
    return 0;
}