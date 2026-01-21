#include <bits/stdc++.h>
using namespace std;

static vector<bool> sievePrimes(int limit) {
    vector<bool> isPrime(limit + 1, true);
    if (limit >= 0) isPrime[0] = false;
    if (limit >= 1) isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= limit; i++) {
        if (!isPrime[i]) continue;
        for (int j = i * i; j <= limit; j += i) isPrime[j] = false;
    }
    return isPrime;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int Lmax = 30 * n;
    const int B = 15 * n;

    // Need primes up to Lmax+2 (for F_i = B + a_i + 3).
    const int LIM = Lmax + 10;
    auto isPrime = sievePrimes(LIM);

    vector<int> F(n + 1, 0);   // prime factor for word as first: F_i = B + a_i + 3
    vector<int> G(n + 1, 0);   // length factor for word as second: G_i = B + a_i + 1 = F_i - 2
    vector<int> a(n + 1, 0);   // prefix length: a_i = F_i - B - 3

    int start = B + 4;
    int endv = Lmax + 2;

    int lastChosen = -1000000000;
    int idx = 1;
    for (int p = start; p <= endv && idx <= n; p++) {
        if (!isPrime[p]) continue;
        if (p - lastChosen == 2) continue; // avoid choosing twin primes -> avoid any G_i == F_j
        F[idx] = p;
        G[idx] = p - 2;
        a[idx] = p - B - 3;
        lastChosen = p;
        idx++;
    }

    if (idx <= n) {
        // Should not happen for given constraints; still output something valid.
        // Fallback: use remaining primes even if twin (may break decoding).
        for (int p = start; p <= endv && idx <= n; p++) {
            if (!isPrime[p]) continue;
            F[idx] = p;
            G[idx] = p - 2;
            a[idx] = p - B - 3;
            idx++;
        }
    }

    string suffix(B, 'X');
    for (int i = 1; i <= n; i++) {
        cout << string(a[i], 'X') << 'O' << suffix << '\n';
    }
    cout.flush();

    vector<int> pos(Lmax + 3, 0);
    for (int i = 1; i <= n; i++) {
        if (G[i] >= 0 && G[i] < (int)pos.size()) pos[G[i]] = i;
    }

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        long long N = p + 1;

        int u = 0;
        for (int i = 1; i <= n; i++) {
            if (F[i] != 0 && (N % F[i] == 0)) {
                u = i;
                break;
            }
        }

        int v = 0;
        if (u != 0) {
            long long gg = N / F[u];
            if (0 <= gg && gg < (long long)pos.size()) v = pos[(int)gg];
        }

        if (u == 0 || v == 0) {
            // Should not happen; output something to keep protocol.
            u = 1; v = 1;
        }

        cout << u << ' ' << v << '\n';
        cout.flush();
    }

    return 0;
}