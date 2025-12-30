#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    long long x, y;
    for (int i = 0; i < N; ++i) cin >> x >> y; // coordinates not needed for validity

    vector<char> isPrime(N, true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int p = 2; 1LL * p * p < N; ++p) {
        if (isPrime[p]) {
            for (long long q = 1LL * p * p; q < N; q += p) isPrime[(int)q] = false;
        }
    }

    int len = N - 1;
    vector<int> A(len);
    for (int i = 0; i < len; ++i) A[i] = i + 1;

    set<int> primePos;
    for (int i = 0; i < len; ++i) if (isPrime[A[i]]) primePos.insert(i);

    // Ensure that at steps t = 10,20,30,... the source city P[t-1] is prime when possible.
    // P positions: P[0]=0, P[1..N-1]=A[0..len-1], P[N]=0.
    // For t=10k => need P[10k-1] prime => A[10k-2] prime (0-based).
    for (int idx = 8; idx < len; idx += 10) {
        if (primePos.find(idx) != primePos.end()) continue;
        auto it = primePos.upper_bound(idx);
        if (it == primePos.end()) break;
        int j = *it;
        swap(A[idx], A[j]);
        primePos.erase(it);
        primePos.insert(idx);
        // A[j] is the previous non-prime at idx, so no need to insert j.
    }

    int K = N + 1;
    string out;
    out.reserve((size_t)K * 8);
    out += to_string(K);
    out.push_back('\n');
    out += "0\n";
    for (int v : A) {
        out += to_string(v);
        out.push_back('\n');
    }
    out += "0\n";
    cout << out;

    return 0;
}