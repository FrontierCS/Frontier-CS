#include <bits/stdc++.h>
using namespace std;

int gcd(int a, int b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x, y;
    cin >> n >> x >> y;

    int d = gcd(x, y);
    int xp = x / d;
    int yp = y / d;
    int L = xp + yp;
    int K = L / 2;  // floor(L/2)

    // Build the independent set pattern of size K in the cycle of length L
    vector<char> inA(L, 0);
    for (int i = 0; i < K; ++i) {
        long long val = (2LL * i * xp) % L;
        inA[val] = 1;
    }

    // Prefix sums over two periods for fast window sum queries
    vector<int> prefix(2 * L + 1, 0);
    for (int i = 0; i < 2 * L; ++i) {
        prefix[i + 1] = prefix[i] + inA[i % L];
    }

    // Function to compute g(r) = max number of ones in any cyclic window of length r
    auto get_g = [&](int r) -> int {
        if (r == 0) return 0;
        int best = 0;
        for (int s = 0; s < L; ++s) {
            int cur = prefix[s + r] - prefix[s];
            if (cur > best) best = cur;
        }
        return best;
    };

    long long Q =