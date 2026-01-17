#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    long long x, y;
    if (!(cin >> n >> x >> y)) return 0;
    
    long long g = std::gcd(x, y);
    long long a = x / g;
    long long b = y / g;
    if (a > b) swap(a, b);
    
    // Number of residues with sizes m0 and m1
    long long c1 = n % g;            // number of residues with size m1 = m0 + 1
    long long c0 = g - c1;           // number of residues with size m0
    long long m0 = n / g;            // floor(n/g)
    long long m1 = m0 + (c1 > 0 ? 1 : 0); // ceil(n/g)
    
    auto ceil_half = [](long long m) -> long long {
        return (m + 1) / 2;
    };
    
    // If both a and b are odd (after dividing by gcd), exact solution: ceil(m/2) per residue
    if ((a & 1LL) && (b & 1LL)) {
        long long s0 = ceil_half(m0);
        long long s1 = ceil_half(m1);
        long long ans = c0 * s0 + c1 * s1;
        cout << ans << "\n";
        return 0;
    }
    
    // One of a or b is even: use greedy with assumed period T = a + b
    long long T = a + b;
    
    auto solve_S = [&](long long m_small, long long m_large) -> pair<long long, long long> {
        // Returns S(m_small), S(m_large)
        if (m_small < T && m_large < T) {
            long long limit = m_large;
            vector<uint8_t> s(limit + 1, 0);
            long long sum = 0;
            long long S_small = 0, S_large = 0;
            for (long long i = 1; i <= limit; ++i) {
                bool ok_a = (i > a) ? (s[i - a] == 0) : true;
                bool ok_b = (i > b) ? (s[i - b] == 0) : true;
                s[i] = (ok_a && ok_b) ? 1 : 0;
                sum += s[i];
                if (i == m_small) S_small = sum;
                if (i == m_large) S_large = sum;
            }
            return {S_small, S_large};
        } else {
            // Need full period to get K, and prefix sums up to r0, r1
            vector<uint8_t> s(T + 1, 0);
            long long K = 0;
            long long r0 = (T == 0 ? 0 : (m_small % T));
            long long r1 = (T == 0 ? 0 : (m_large % T));
            long long P0 = (r0 == 0 ? 0 : -1);
            long long P1 = (r1 == 0 ? 0 : -1);
            long long sum = 0;
            for (long long i = 1; i <= T; ++i) {
                bool ok_a = (i > a) ? (s[i - a] == 0) : true;
                bool ok_b = (i > b) ? (s[i - b] == 0) : true;
                s[i] = (ok_a && ok_b) ? 1 : 0;
                sum += s[i];
                if (i == r0 && r0 != 0) P0 = sum;
                if (i == r1 && r1 != 0) P1 = sum;
            }
            K = sum;
            if (P0 == -1) P0 = 0;
            if (P1 == -1) P1 = 0;
            long long S_small = (T == 0 ? 0 : (m_small / T) * K + P0);
            long long S_large = (T == 0 ? 0 : (m_large / T) * K + P1);
            return {S_small, S_large};
        }
    };
    
    auto [S0, S1] = solve_S(m0, m1);
    long long ans = c0 * S0 + c1 * S1;
    cout << ans << "\n";
    return 0;
}