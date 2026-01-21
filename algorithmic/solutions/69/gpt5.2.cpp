#include <bits/stdc++.h>
using namespace std;

static vector<int> sievePrimes(int N) {
    vector<bool> isPrime(N + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= N; i++) if (isPrime[i]) {
        for (long long j = 1LL * i * i; j <= N; j += i) isPrime[(int)j] = false;
    }
    vector<int> primes;
    primes.reserve(N / 10);
    for (int i = 2; i <= N; i++) if (isPrime[i]) primes.push_back(i);
    return primes;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int L = 15 * n;
    const int maxLen = 30 * n;

    vector<int> primes = sievePrimes(maxLen + 5);

    vector<int> U;
    U.reserve(n);

    int low = L + 2;
    int high = maxLen;

    for (int p : primes) {
        if (p < low) continue;
        if (p > high) break;
        if (!U.empty() && p - U.back() == 2) continue; // avoid selecting both of a twin-prime pair
        U.push_back(p);
        if ((int)U.size() == n) break;
    }

    if ((int)U.size() != n) {
        // Fallback (should not happen for given constraints)
        // Just take primes from anywhere up to maxLen (still try to avoid twin pairs).
        U.clear();
        for (int p : primes) {
            if (p < 3) continue;
            if (p > maxLen) break;
            if (!U.empty() && p - U.back() == 2) continue;
            U.push_back(p);
            if ((int)U.size() == n) break;
        }
    }

    string prefix(L, 'X');

    vector<int> pos(maxLen + 10, -1);
    for (int i = 0; i < n; i++) {
        int b = U[i] - L - 1; // >= 1
        if (b < 1) b = 1;
        int len = L + 1 + b;
        if (len > maxLen) b = max(1, maxLen - L - 1);

        cout << prefix << 'O' << string(b, 'X') << '\n';
        if (U[i] >= 0 && U[i] < (int)pos.size()) pos[U[i]] = i + 1;
    }
    cout.flush();

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        long long x = p + 1;

        int u = -1;
        for (int i = 0; i < n; i++) {
            int pu = U[i];
            if (pu != 0 && x % pu == 0) {
                u = i + 1;
                break;
            }
        }

        int v = -1;
        if (u != -1) {
            long long quo = x / U[u - 1];
            long long uv = quo - 2;
            if (uv >= 0 && uv < (long long)pos.size()) v = pos[(int)uv];
        }

        if (u == -1 || v == -1) {
            u = 1; v = 1;
        }

        cout << u << ' ' << v << '\n';
        cout.flush();
    }

    return 0;
}