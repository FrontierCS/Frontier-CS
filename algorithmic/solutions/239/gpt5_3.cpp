#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    
    long long N = n;
    int B = 1;
    while (1LL * B * B * B < N + 1) ++B; // smallest B with B^3 >= n+1
    
    long long m = 0;

    // S0: lengths 2..min(n, B-1)
    int S0_end = min(n, B - 1);
    for (int d = 2; d <= S0_end; ++d) {
        m += (n - d + 1);
    }

    // S1: lengths t*B for t=1..min(B-1, n/B)
    int M1 = min(B - 1, n / B);
    for (int t = 1; t <= M1; ++t) {
        int L = t * B;
        m += (n - L + 1);
    }

    // S2: lengths t*B^2 for t=1..min(B-1, n/B^2)
    int B2 = B * B;
    int M2 = min(B - 1, n / B2);
    for (int t = 1; t <= M2; ++t) {
        int L = t * B2;
        m += (n - L + 1);
    }

    cout << m << "\n";

    // Output triples
    // S0
    for (int d = 2; d <= S0_end; ++d) {
        int L = d;
        int x = 1; // L = 1 + (L-1), and (L-1) was added earlier
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + x;
            int v = i + L;
            cout << u << " " << c << " " << v << "\n";
        }
    }

    // S1
    for (int t = 1; t <= M1; ++t) {
        int L = t * B;
        int x;
        if (t == 1) x = 1;          // B = 1 + (B-1)
        else x = (t - 1) * B;       // tB = (t-1)B + B
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + x;
            int v = i + L;
            cout << u << " " << c << " " << v << "\n";
        }
    }

    // S2
    for (int t = 1; t <= M2; ++t) {
        int L = t * B2;
        int x;
        if (t == 1) x = B;          // B^2 = B + (B-1)B
        else x = (t - 1) * B2;      // tB^2 = (t-1)B^2 + B^2
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + x;
            int v = i + L;
            cout << u << " " << c << " " << v << "\n";
        }
    }

    return 0;
}