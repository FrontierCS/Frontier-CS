#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    // Maximum distance is n (from 0 to n). We ensure any distance can be covered by at most 3 edges
    // by adding all edges of length up to T, where 3*T >= n.
    long long T = (n + 2) / 3; // ceil(n/3)
    long long m = 0;

    // Count edges: for each a, we add edges a->a+t for t=2..min(T, n-a)
    for (long long a = 0; a <= n - 1; ++a) {
        long long cap = min(T, n - a);
        if (cap >= 2) m += (cap - 1);
    }

    cout << m << '\n';
    for (long long a = 0; a <= n - 1; ++a) {
        long long cap = min(T, n - a);
        for (long long t = 2; t <= cap; ++t) {
            long long c = a + t - 1;
            long long v = a + t;
            cout << a << ' ' << c << ' ' << v << '\n';
        }
    }
    return 0;
}