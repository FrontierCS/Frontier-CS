#include <bits/stdc++.h>
using namespace std;

struct Op {
    int L, L1, L2;
};

long long compute_m(int n, int A) {
    long long m = 0;
    // Small residues 2..A-1
    for (int L = 2; L < A && L <= n; ++L) m += (n - L + 1);
    // Multiples of A: s*A, s=1..A-1
    for (int s = 1; s < A; ++s) {
        long long L = 1LL * s * A;
        if (L <= n) m += (n - L + 1);
    }
    // Multiples of A^2
    long long base = 1LL * A * A;
    for (long long L = base; L <= n; L += base) m += (n - L + 1);
    return m;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n <= 1) {
        cout << 0 << "\n";
        return 0;
    }

    int maxA = min(n, 256);
    long long bestM = LLONG_MAX;
    int bestA = 2;
    for (int A = 2; A <= maxA; ++A) {
        long long m = compute_m(n, A);
        if (m < bestM) {
            bestM = m;
            bestA = A;
        }
    }
    int A = bestA;

    vector<Op> ops;
    // Step 1: lengths 2..A-1
    for (int L = 2; L < A && L <= n; ++L) {
        ops.push_back({L, 1, L - 1});
    }
    // Step 2: length A
    if (A <= n) {
        int L1 = A / 2;
        int L2 = A - L1;
        ops.push_back({A, L1, L2});
    }
    // Step 3: multiples s*A for s=2..A-1
    for (int s = 2; s < A; ++s) {
        long long L = 1LL * s * A;
        if (L <= n) {
            ops.push_back({(int)L, (s - 1) * A, A});
        }
    }
    // Step 4: A^2
    long long base = 1LL * A * A;
    if (base <= n) {
        int s = A / 2;
        int L1 = s * A;
        int L2 = (int)base - L1;
        ops.push_back({(int)base, L1, L2});
    }
    // Step 5: multiples of A^2
    for (long long k = 2; k * base <= n; ++k) {
        long long L = k * base;
        ops.push_back({(int)L, (int)((k - 1) * base), (int)base});
    }

    long long m = 0;
    for (auto &op : ops) {
        m += (n - op.L + 1);
    }

    cout << m << "\n";
    for (auto &op : ops) {
        int L = op.L, L1 = op.L1, L2 = op.L2;
        for (int i = 0; i + L <= n; ++i) {
            int u = i;
            int c = i + L1;
            int v = i + L;
            cout << u << " " << c << " " << v << "\n";
        }
    }

    return 0;
}