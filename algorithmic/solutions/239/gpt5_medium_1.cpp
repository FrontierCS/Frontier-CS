#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    if (n <= 1) {
        cout << 0 << '\n';
        return 0;
    }
    
    // Compute smallest M such that M^3 >= n
    int M = 1;
    while (1LL * M * M * M < n) ++M;
    
    vector<array<int,3>> edges;
    // Rough reservation to reduce reallocations
    int q1 = n / M;
    int q2 = n / (M * M);
    edges.reserve(n * (M + q1 + q2 + 5));
    
    auto add_length_using_A = [&](int L, int A){
        int B = L - A;
        // assume edges of length A and B already exist for all positions
        for (int i = 0; i + L <= n; ++i) {
            edges.push_back({i, i + A, i + L});
        }
    };
    
    // Stage 1: small lengths 2..M-1 (length 1 already exists initially)
    for (int L = 2; L <= M - 1; ++L) {
        add_length_using_A(L, 1); // use 1 + (L-1)
    }
    
    // Stage 2: medium lengths multiples of M: M, 2M, ..., (M-1)M (as needed)
    if (M <= n) {
        add_length_using_A(M, 1); // M = 1 + (M-1)
    }
    int maxT = min(M - 1, n / M);
    for (int t = 2; t <= maxT; ++t) {
        int L = t * M;
        add_length_using_A(L, L - M); // (t-1)M + M
    }
    
    // Stage 3: large lengths multiples of M^2: M^2, 2M^2, ...
    int MSq = M * M;
    if (MSq <= n) {
        // Build M^2 = (M-1)*M + M
        add_length_using_A(MSq, (M - 1) * M);
        int maxK = n / MSq;
        for (int k = 2; k <= maxK; ++k) {
            int L = k * MSq;
            add_length_using_A(L, L - MSq); // (k-1)M^2 + M^2
        }
    }
    
    cout << edges.size() << '\n';
    for (auto &e : edges) {
        cout << e[0] << ' ' << e[1] << ' ' << e[2] << '\n';
    }
    return 0;
}