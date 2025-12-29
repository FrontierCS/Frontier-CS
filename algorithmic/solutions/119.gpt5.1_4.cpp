#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

long long query(const vector<long long>& a) {
    cout << "?";
    for (long long x : a) {
        cout << ' ' << x;
    }
    cout << '\n';
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0); // in case of EOF / error
    if (res == -1) exit(0);     // conventional interactive failure
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const long long a0 = 1000000; // any value in [1, MOD-1] far from 1
    vector<long long> a(n + 1);
    a[0] = a0;
    for (int i = 1; i <= n; ++i) a[i] = 1;

    // Baseline query: all a_i = 1 for i >= 1
    long long y0 = query(a);

    // Total number of '+' operators
    long long S = (y0 - a0) % MOD;
    if (S < 0) S += MOD;
    // Since 0 <= S <= n < MOD, this is exact
    int totalPlus = (int)S;

    vector<int> isPlus(n + 1, 0); // 1 if '+', 0 if '*'

    // For k = 1..n-1, change a_k from 1 to 2 and compare
    for (int k = 1; k <= n - 1; ++k) {
        a[k] = 2;
        long long yk = query(a);
        long long delta = (yk - y0) % MOD;
        if (delta < 0) delta += MOD;
        if (delta == 1) {
            isPlus[k] = 1; // '+'
        } else {
            isPlus[k] = 0; // '*'
        }
        a[k] = 1; // restore for next queries
    }

    int knownPlus = 0;
    for (int i = 1; i <= n - 1; ++i) knownPlus += isPlus[i];
    int lastPlus = totalPlus - knownPlus;
    if (lastPlus < 0) lastPlus = 0;
    if (lastPlus > 1) lastPlus = 1;
    isPlus[n] = lastPlus;

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        int op = (isPlus[i] ? 0 : 1); // 0 for '+', 1 for '*'
        cout << ' ' << op;
    }
    cout << '\n';
    cout.flush();

    return 0;
}