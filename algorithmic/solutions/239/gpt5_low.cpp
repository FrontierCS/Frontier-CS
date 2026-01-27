#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if(!(cin >> n)) return 0;

    // For n <= 3, no need to add edges (paths already <= 3 edges)
    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    // Choose B as power of two around n^(1/3), at least 2
    auto is_pow2 = [](long long x){ return x && ((x & (x-1)) == 0); };
    long long B = 1;
    while ((B<<1) * (B<<1) * (B<<1) <= n) B <<= 1;
    if (B < 2) B = 2;

    vector<tuple<int,int,int>> ops;

    auto add_length = [&](int L, int a){
        // add edge (u -> u+L) using intermediate u+a for all valid u
        for (int u = 0; u + L <= (int)n; ++u) {
            int c = u + a;
            int v = u + L;
            ops.emplace_back(u, c, v);
        }
    };

    // Build lengths 2..B-1 using 1 + (L-1)
    for (int L = 2; L <= (int)min<long long>(B-1, n); ++L) {
        add_length(L, 1);
    }

    // Build B using B/2 + B/2 (B is power of two)
    if (B <= n) {
        add_length((int)B, (int)(B/2));
    }

    // Build multiples of B: kB for k=2..min(B-1, n/B) using (k-1)B + B
    long long maxK = min(B-1, n / B);
    for (int k = 2; k <= (int)maxK; ++k) {
        int L = (int)(k * B);
        int a = (int)((k-1) * B);
        add_length(L, a);
    }

    // Build B^2 using (B-1)B + B
    long long B2 = B * B;
    if (B2 <= n) {
        int a = (int)((B-1) * B);
        if (a == 0) a = (int)(B/2); // safety, though B>=2 ensures a>0 when B>=2
        add_length((int)B2, a);
    }

    // Build multiples of B^2: c*B^2 for c=2..floor(n/B^2) using (c-1)B^2 + B^2
    if (B2 <= n) {
        long long maxC = n / B2;
        for (int c = 2; c <= (int)maxC; ++c) {
            int L = (int)(c * B2);
            int a = (int)((c-1) * B2);
            add_length(L, a);
        }
    }

    cout << ops.size() << "\n";
    for (auto &t : ops) {
        int u, c, v;
        tie(u, c, v) = t;
        cout << u << " " << c << " " << v << "\n";
    }
    return 0;
}