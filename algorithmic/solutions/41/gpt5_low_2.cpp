#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if(!(cin >> n)) return 0;

    unsigned long long p = 1;
    int t = 0;
    while (p <= n / 2) { // ensure p*2 <= n
        p <<= 1;
        t++;
    }
    // Now p = 2^t, the largest power of two <= n
    unsigned long long b = n / p; // floor(n / 2^t), >=1

    int k = t + 1;
    cout << k << "\n";
    for (int i = 0; i <= t; ++i) {
        unsigned long long ai = b * (1ULL << i);
        if (i) cout << ' ';
        cout << ai;
    }
    cout << "\n";
    return 0;
}