#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if(!(cin >> n)) return 0;

    vector<unsigned long long> pow2;
    pow2.push_back(1);
    for (int i = 1; i <= 62; ++i) {
        if (pow2.back() > ULLONG_MAX / 2) break;
        pow2.push_back(pow2.back() * 2);
    }

    int best_k = 1;
    unsigned long long best_b = n; // for k=1, b = n
    __int128 bestV = (__int128)1 * n * (pow2[1] - 1); // (2^1 -1)=1

    int maxK = 1;
    while (maxK - 1 < (int)pow2.size() && pow2[maxK - 1] <= n) ++maxK;
    --maxK; // last valid k

    for (int k = 1; k <= maxK; ++k) {
        unsigned long long denom = pow2[k - 1];
        unsigned long long b = n / denom;
        unsigned long long sumFactor = pow2[k] - 1; // 2^k - 1
        __int128 V = (__int128)k * (__int128)b * (__int128)sumFactor;
        if (V > bestV) {
            bestV = V;
            best_k = k;
            best_b = b;
        }
    }

    cout << best_k << "\n";
    for (int i = 0; i < best_k; ++i) {
        unsigned long long val = best_b * pow2[i];
        if (i) cout << ' ';
        cout << val;
    }
    cout << "\n";
    return 0;
}