#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using ll = long long;

static inline ull hilbertIndex(uint32_t x, uint32_t y, int K) {
    ull d = 0;
    ull n = 1ULL << K;
    for (ull s = n >> 1; s; s >>= 1) {
        ull rx = (x & s) ? 1 : 0;
        ull ry = (y & s) ? 1 : 0;
        d += s * s * ((3 * rx) ^ ry);
        if (ry == 0) {
            if (rx == 1) {
                x = (uint32_t)(n - 1 - x);
                y = (uint32_t)(n - 1 - y);
            }
            swap(x, y);
        }
    }
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<ll> xs(N), ys(N);
    for (int i = 0; i < N; ++i) cin >> xs[i] >> ys[i];

    // Sieve primes up to N-1
    vector<char> isPrime(max(2, N), true);
    isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; (ll)i * i <= N - 1; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j <= N - 1; j += i) isPrime[j] = false;
        }
    }

    // Normalize coordinates for Hilbert
    ll minX = xs[0], minY = ys[0];
    ll maxX = xs[0], maxY = ys[0];
    for (int i = 0; i < N; ++i) {
        minX = min(minX, xs[i]);
        minY = min(minY, ys[i]);
        maxX = max(maxX, xs[i]);
        maxY = max(maxY, ys[i]);
    }
    ull rangeX = (ull)(maxX - minX);
    ull rangeY = (ull)(maxY - minY);
    ull maxCoord = max(rangeX, rangeY);
    int K = 0;
    while ((1ULL << K) <= maxCoord) ++K;
    if (K == 0) K = 1; // handle all points equal case

    vector<uint32_t> nx(N), ny(N);
    for (int i = 0; i < N; ++i) {
        ull X = (ull)(xs[i] - minX);
        ull Y = (ull)(ys[i] - minY);
        nx[i] = (uint32_t)X;
        ny[i] = (uint32_t)Y;
    }

    // Compute Hilbert order values for all cities
    vector<ull> hv(N);
    for (int i = 0; i < N; ++i) {
        hv[i] = hilbertIndex(nx[i], ny[i], K);
    }

    // Prepare sorted indices (excluding 0) by Hilbert
    vector<int> ids;
    ids.reserve(max(0, N - 1));
    for (int i = 1; i < N; ++i) ids.push_back(i);
    sort(ids.begin(), ids.end(), [&](int a, int b) {
        if (hv[a] != hv[b]) return hv[a] < hv[b];
        return a < b;
    });

    // Split into primes and non-primes according to Hilbert order
    vector<int> primesList;
    vector<int> nonprimesList;
    primesList.reserve(ids.size());
    nonprimesList.reserve(ids.size());
    for (int id : ids) {
        if (isPrime[id]) primesList.push_back(id);
        else nonprimesList.push_back(id);
    }

    // Build target mask for positions in seq (k = 0..N-2). Need P[k] prime when (k+2) % 10 == 0.
    int M = N - 1; // length of seq
    vector<char> target(max(0, M), 0);
    for (int k = 0; k < M; ++k) {
        if (((k + 2) % 10) == 0) target[k] = 1;
    }
    vector<int> suffixTargets(M + 1, 0);
    for (int k = M - 1; k >= 0; --k) suffixTargets[k] = suffixTargets[k + 1] + (target[k] ? 1 : 0);

    auto dist2 = [&](int a, int b) -> long double {
        long double dx = (long double)xs[a] - (long double)xs[b];
        long double dy = (long double)ys[a] - (long double)ys[b];
        return dx * dx + dy * dy;
    };

    vector<int> seq;
    seq.resize(max(0, M));
    size_t ip = 0, in = 0;
    int lastId = 0;
    for (int k = 0; k < M; ++k) {
        if (target[k]) {
            if (ip < primesList.size()) {
                seq[k] = primesList[ip++];
            } else if (in < nonprimesList.size()) {
                seq[k] = nonprimesList[in++];
            } else {
                // Shouldn't happen, but fallback
                seq[k] = 1; // any valid id, though this case is unlikely
            }
        } else {
            size_t primesRemaining = primesList.size() - ip;
            int targetsRemaining = suffixTargets[k + 1];
            bool canUsePrime = (primesRemaining > (size_t)targetsRemaining);
            bool hasNonPrime = in < nonprimesList.size();
            if (hasNonPrime && canUsePrime) {
                // choose closer to lastId
                int candN = nonprimesList[in];
                int candP = primesList[ip];
                long double dn = dist2(lastId, candN);
                long double dp = dist2(lastId, candP);
                if (dp < dn) {
                    seq[k] = candP; ++ip;
                } else {
                    seq[k] = candN; ++in;
                }
            } else if (hasNonPrime) {
                seq[k] = nonprimesList[in++];
            } else if (canUsePrime) {
                seq[k] = primesList[ip++];
            } else {
                // No non-primes left and primes are exactly reserved for future targets,
                // but since k is non-target, we should still safely take a prime.
                // This situation effectively can't violate future constraints due to counts,
                // but we handle it regardless.
                if (ip < primesList.size()) {
                    seq[k] = primesList[ip++];
                } else {
                    // Absolute fallback (should not happen)
                    seq[k] = 1;
                }
            }
        }
        lastId = seq[k];
    }

    // Output route
    cout << (N + 1) << '\n';
    cout << 0 << '\n';
    for (int k = 0; k < M; ++k) cout << seq[k] << '\n';
    cout << 0 << '\n';

    return 0;
}