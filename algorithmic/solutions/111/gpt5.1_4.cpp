#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;
    
    long long half = n / 2;
    int T = (int) sqrt((long double)half);
    while (1LL * (T + 1) * (T + 1) <= half) ++T;
    while (1LL * T * T > half) --T;
    if (n >= 1 && T == 0) T = 1; // ensure at least one element when possible
    
    if (n == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }
    
    // Determine number of bits needed for XOR values
    int k = 0;
    while ((1LL << k) <= n) ++k;
    int G = 1 << k; // max XOR value space size (2^k)
    
    // usedXor[v] == run_id means XOR value v is already used in this run
    vector<int> usedXor(G, 0);
    
    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    vector<int> bestS;
    int bestSize = 0;
    
    int maxIter = 4;
    int run_id = 0;
    
    for (int it = 0; it < maxIter; ++it) {
        ++run_id;
        vector<int> curS;
        curS.reserve(T + 5);
        vector<int> tmpXors;
        tmpXors.reserve(T + 5);
        
        long long step = 1;
        if (n > 1) {
            uniform_int_distribution<long long> distStep(1, n - 1);
            // choose step coprime with n to generate a permutation
            for (int tries = 0; tries < 60; ++tries) {
                step = distStep(rng);
                if (std::gcd(step, n) == 1) break;
            }
            if (std::gcd(step, n) != 1) step = 1;
        }
        
        uniform_int_distribution<long long> distStart(0, n - 1);
        long long start = distStart(rng);
        
        for (long long idx = 0; idx < n && (int)curS.size() < T; ++idx) {
            long long x = (start + (__int128)step * idx) % n + 1;
            int xi = (int)x;
            bool ok = true;
            tmpXors.clear();
            for (int a : curS) {
                int v = a ^ xi;
                if (usedXor[v] == run_id) {
                    ok = false;
                    break;
                }
                tmpXors.push_back(v);
            }
            if (ok) {
                curS.push_back(xi);
                for (int v : tmpXors) usedXor[v] = run_id;
            }
        }
        
        if ((int)curS.size() > bestSize) {
            bestSize = (int)curS.size();
            bestS = curS;
        }
        if (bestSize >= T) break;
    }
    
    // If somehow we still didn't reach T (very unlikely), fallback:
    // Greedy sequential without permutation (deterministic).
    if (bestSize < T) {
        ++run_id;
        vector<int> curS;
        curS.reserve(T + 5);
        vector<int> tmpXors;
        tmpXors.reserve(T + 5);
        for (int x = 1; x <= n && (int)curS.size() < T; ++x) {
            bool ok = true;
            tmpXors.clear();
            for (int a : curS) {
                int v = a ^ x;
                if (usedXor[v] == run_id) {
                    ok = false;
                    break;
                }
                tmpXors.push_back(v);
            }
            if (ok) {
                curS.push_back(x);
                for (int v : tmpXors) usedXor[v] = run_id;
            }
        }
        if ((int)curS.size() > bestSize) {
            bestSize = (int)curS.size();
            bestS = curS;
        }
    }
    
    // Output result
    cout << bestSize << "\n";
    for (int i = 0; i < bestSize; ++i) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << "\n";
    
    return 0;
}