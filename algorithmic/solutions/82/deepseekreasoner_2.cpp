#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    // precompute count of numbers in [0, n-1] with bit k set
    const int MAX_BIT = 11; // because n <= 2048, 2^11 = 2048
    vector<int> cnt_bit(MAX_BIT, 0);
    for (int k = 0; k < MAX_BIT; ++k) {
        int block = 1 << (k+1);
        cnt_bit[k] = (n / block) * (1 << k);
        int rem = n % block;
        if (rem > (1 << k))
            cnt_bit[k] += rem - (1 << k);
    }

    // Step 1: query OR(1, i) for i = 2..n
    vector<int> B(n+1, 0); // B[i] for i>=2
    for (int i = 2; i <= n; ++i) {
        cout << "? 1 " << i << endl;
        cin >> B[i];
        if (B[i] == -1) return 0;
    }

    // Step 2: deduce p1
    int p1 = 0;
    for (int k = 0; k < MAX_BIT; ++k) {
        int m = 0;
        for (int i = 2; i <= n; ++i) {
            if ((B[i] >> k) & 1) ++m;
        }
        if (m != cnt_bit[k]) {
            p1 |= (1 << k);
        }
    }

    vector<int> p(n+1, 0);
    p[1] = p1;

    if (p1 == 0) {
        // p1 is zero, so p[i] = B[i]
        for (int i = 2; i <= n; ++i) {
            p[i] = B[i];
        }
    } else {
        // Step 3: query OR(i, i+1) for i = 1..n-1
        vector<int> C(n, 0); // C[i] for i=1..n-1
        for (int i = 1; i <= n-1; ++i) {
            cout << "? " << i << " " << i+1 << endl;
            cin >> C[i];
            if (C[i] == -1) return 0;
        }

        // For each bit, reconstruct
        for (int k = 0; k < MAX_BIT; ++k) {
            vector<int> x(n+1, 0); // x[i] will be bit k of p[i]
            x[1] = (p1