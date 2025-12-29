#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned int n;
    if (!(cin >> n)) return 0;

    if (n <= 4) {
        cout << n << "\n";
        for (unsigned int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << "\n";
        return 0;
    }

    int B = 32 - __builtin_clz(n);      // number of bits to represent n
    int floorLog = B - 1;               // floor(log2 n)
    int k0 = floorLog / 2;              // largest k with 2^(2k) <= n, k >= 1

    static const int irr[13] = {
        0,
        0x3,      // x + 1
        0x7,      // x^2 + x + 1
        0xB,      // x^3 + x + 1
        0x13,     // x^4 + x + 1
        0x25,     // x^5 + x^2 + 1
        0x43,     // x^6 + x + 1
        0x89,     // x^7 + x^3 + 1
        0x11D,    // x^8 + x^4 + x^3 + x + 1
        0x211,    // x^9 + x^4 + 1
        0x409,    // x^10 + x^3 + 1
        0x805,    // x^11 + x^2 + 1
        0x1009    // x^12 + x^3 + 1
    };

    auto gfMul = [&](int a, int b) -> int {
        int res = 0;
        int poly = irr[k0];
        while (b) {
            if (b & 1) res ^= a;
            b >>= 1;
            a <<= 1;
            if (a & (1 << k0)) a ^= poly;
        }
        return res;
    };

    auto gfPow3 = [&](int x) -> int {
        if (!x) return 0;
        int x2 = gfMul(x, x);
        return gfMul(x2, x);
    };

    vector<unsigned int> S;
    S.reserve(4096);
    vector<uint8_t> inS(n + 1, 0);

    unsigned int limit = 1u << k0;
    for (unsigned int x = 0; x < limit; ++x) {
        int c = gfPow3((int)x);
        unsigned int val = x | (unsigned(c) << k0); // 2k0-bit number
        if (val == 0 || val > n) continue;
        if (!inS[val]) {
            inS[val] = 1;
            S.push_back(val);
        }
    }

    vector<uint8_t> usedXor(1u << B, 0);

    for (size_t i = 0; i < S.size(); ++i) {
        for (size_t j = i + 1; j < S.size(); ++j) {
            unsigned int v = S[i] ^ S[j];
            usedXor[v] = 1;
        }
    }

    long long half = n / 2;
    int L = (int) sqrt((long double)half);
    while ((long long)(L + 1) * (L + 1) <= half) ++L;
    while ((long long)L * L > half) --L;
    if (L < 1) L = 1;
    int target = L;

    if (S.size() < (size_t)target) {
        for (unsigned int cand = 1; cand <= n && S.size() < (size_t)target; ++cand) {
            if (inS[cand]) continue;
            bool ok = true;
            for (unsigned int a : S) {
                unsigned int v = a ^ cand;
                if (usedXor[v]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                for (unsigned int a : S) {
                    unsigned int v = a ^ cand;
                    usedXor[v] = 1;
                }
                inS[cand] = 1;
                S.push_back(cand);
            }
        }
    }

    cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << "\n";

    return 0;
}