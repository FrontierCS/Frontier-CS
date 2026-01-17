#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    auto bits = [](unsigned long long x) -> int {
        if (x == 0) return 0;
        return 64 - __builtin_clzll(x + 1ull);
    };

    // Query with a = 1
    cout << "? " << 1 << "\n" << flush;
    long long T1;
    if (!(cin >> T1)) return 0;

    // Query with a = n-1  (i.e., -1 mod n)
    long long aneg = (n - 1 + n) % n;
    cout << "? " << aneg << "\n" << flush;
    long long Tneg;
    if (!(cin >> Tneg)) return 0;

    // Popcount of d from T1: T1 = 240 + 4 * popcnt(d)
    long long P = (T1 - 240) / 4;

    // Determine d0 using Tneg
    int b = bits((unsigned long long)(n - 1));
    long long B0 = b + 1; // bits(n-1)+1

    long long Tneg0 = B0 * B0 + 236 + 4 * P;       // assuming d0 = 0
    long long Tneg1 = B0 * B0 + 236 + 2 * B0 * P;  // assuming d0 = 1

    int d0;
    if (Tneg == Tneg0) d0 = 0;
    else d0 = 1;

    // Construct a guess for d having popcount P and LSB d0.
    unsigned long long d = 0;
    if (d0) d |= 1ull;
    long long remaining = P - d0;
    for (int i = 1; i < 60 && remaining > 0; ++i) {
        d |= (1ull << i);
        --remaining;
    }

    cout << "! " << d << "\n" << flush;
    return 0;
}