#include <bits/stdc++.h>
using namespace std;

long long count_edges(int n, int b) {
    long long m = 0;
    int t1 = min(b, n);
    for (int L = 2; L <= t1; ++L) {
        m += (n - L + 1);
    }
    for (int k = 2; k <= b; ++k) {
        long long L = 1LL * k * b;
        if (L > n) break;
        m += (n - L + 1);
    }
    long long b2 = 1LL * b * b;
    long long t = n / b2;
    for (long long i = 2; i <= t; ++i) {
        long long L = i * b2;
        m += (n - L + 1);
    }
    return m;
}

void print_edges(int n, int b) {
    int t1 = min(b, n);
    for (int L = 2; L <= t1; ++L) {
        for (int u = 0; u + L <= n; ++u) {
            int c = u + (L - 1);
            int v = u + L;
            cout << u << ' ' << c << ' << v << '\n';
        }
    }
    for (int k = 2; k <= b; ++k) {
        long long L = 1LL * k * b;
        if (L > n) break;
        for (int u = 0; u + L <= n; ++u) {
            int c = u + (k - 1) * b;
            int v = u + k * b;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }
    long long b2 = 1LL * b * b;
    long long t = n / b2;
    for (long long i = 2; i <= t; ++i) {
        long long L = i * b2;
        for (int u = 0; u + L <= n; ++u) {
            long long c = u + (i - 1) * b2;
            long long v = u + i * b2;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n <= 1) {
        cout << 0 << '\n';
        return 0;
    }

    int bestB = 2;
    long long bestM = count_edges(n, 2);
    for (int b = 3; b <= n; ++b) {
        long long m = count_edges(n, b);
        if (m < bestM) {
            bestM = m;
            bestB = b;
        }
    }

    cout << bestM << '\n';
    // Stage 1: lengths 2..b
    int b1 = min(bestB, n);
    for (int L = 2; L <= b1; ++L) {
        for (int u = 0; u + L <= n; ++u) {
            int c = u + (L - 1);
            int v = u + L;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }
    // Stage 2: multiples of b up to b^2
    for (int k = 2; k <= bestB; ++k) {
        long long L = 1LL * k * bestB;
        if (L > n) break;
        for (int u = 0; u + L <= n; ++u) {
            int c = u + (k - 1) * bestB;
            int v = u + k * bestB;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }
    // Stage 3: multiples of b^2
    long long b2 = 1LL * bestB * bestB;
    long long t = n / b2;
    for (long long i = 2; i <= t; ++i) {
        long long L = i * b2;
        for (int u = 0; u + L <= n; ++u) {
            long long c = u + (i - 1) * b2;
            long long v = u + i * b2;
            cout << u << ' ' << c << ' ' << v << '\n';
        }
    }

    return 0;
}