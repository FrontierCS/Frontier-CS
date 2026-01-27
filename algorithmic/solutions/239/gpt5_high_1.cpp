#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if(!(cin >> n)) return 0;
    long long N = n; // maximum distance
    
    if (N <= 1) {
        cout << 0 << "\n";
        return 0;
    }
    
    // Find smallest power of two B such that B^3 >= N
    long long B = 1;
    while (B * B * B < N) B <<= 1;
    
    vector<pair<int,int>> lengths; // (d, a) where d = a + b, both previously available
    
    auto add_len = [&](int d, int a){
        if(d <= 0 || a <= 0 || a >= d) return;
        if(d > N) return;
        lengths.emplace_back(d, a);
    };
    
    // 1) Add lengths 2..min(B-1, N) using (d-1)+1
    int upper_small = (int)min<long long>(N, max(1LL, B - 1));
    for (int d = 2; d <= upper_small; ++d) {
        add_len(d, d - 1);
    }
    
    // 2) Add multiples of B: B, 2B, ..., min(B^2 - B, N)
    if (B <= N) {
        int kmax = (int)min<long long>(B - 1, N / B);
        for (int k = 1; k <= kmax; ++k) {
            int d = (int)(k * B);
            if (k == 1) add_len(d, (int)(B - 1)); // B = (B-1) + 1
            else add_len(d, (int)((k - 1) * B));  // kB = (k-1)B + B
        }
    }
    
    // 3) Add B^2 and its multiples up to min(B^3 - B^2, N)
    if (B * B <= N) {
        int d = (int)(B * B);
        add_len(d, (int)((B/2) * B)); // B^2 = (B/2)B + (B/2)B (B is power of two)
        int amax = (int)min<long long>(B - 1, N / (B * B));
        for (int a = 2; a <= amax; ++a) {
            int d2 = a * (int)(B * B);
            add_len(d2, (a - 1) * (int)(B * B)); // aB^2 = (a-1)B^2 + B^2
        }
    }
    
    // 4) Special case: if N == B^3, add direct edge of length N using N/2 + N/2
    if (B * B * B == N) {
        add_len((int)N, (int)(N / 2));
    }
    
    // Count total edges
    long long m = 0;
    for (auto &p : lengths) {
        int d = p.first;
        m += (n - d + 1);
    }
    
    cout << m << "\n";
    
    // Output triples in the same order
    for (auto &p : lengths) {
        int d = p.first;
        int a = p.second;
        for (int u = 0; u + d <= n; ++u) {
            int c = u + a;
            int v = u + d;
            cout << u << " " << c << " " << v << "\n";
        }
    }
    return 0;
}