#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    if (n == 0) {
        cout << 1 << endl << 1 << endl;
        return 0;
    }

    // Generate primes up to 1e6 + margin
    const int MAXP = 1000100;
    vector<bool> is_prime(MAXP, true);
    is_prime[0] = is_prime[1] = false;
    for (long long i = 2; i < MAXP; ++i) {
        if (is_prime[i]) {
            for (long long j = i * i; j < MAXP; j += i) {
                if (j >= MAXP) break;
                is_prime[j] = false;
            }
        }
    }
    vector<long long> primes;
    for (int i = 2; i < MAXP; ++i) {
        if (is_prime[i]) primes.push_back(i);
    }

    // Power of 2 sequence
    vector<long long> powseq;
    long long current = 1;
    powseq.push_back(1);
    while ((current *= 2) <= n) {
        powseq.push_back(current);
    }

    // Prime sequence
    vector<long long> seq;
    if (n >= 1) seq.push_back(1);
    if (n >= 2) seq.push_back(2);
    size_t cur = 1;
    while (cur < primes.size()) {
        long long pa = primes[cur - 1];
        long long pb = primes[cur];
        __int128 nextv = (__int128)pa * pb;
        if (nextv > n) break;
        long long nv = (long long)nextv;
        if (nv <= seq.back()) break;
        seq.push_back(nv);
        ++cur;
    }

    // Add the last term for prime sequence
    if (seq.size() >= 2) {
        long long pm = primes[cur - 1];
        long long last = seq.back();
        long long remaining = (last == pm ? 1LL : last / pm);
        long long min_r = (last + pm) / pm;
        long long max_r = n / pm;
        if (max_r >= min_r) {
            long long r = max_r;
            while (r >= min_r && __gcd(r, remaining) != 1) {
                --r;
            }
            if (r >= min_r) {
                long long newa = pm * r;
                if (newa <= n && newa > last) {
                    seq.push_back(newa);
                }
            }
        }
    }

    // Compute sums
    long long sum_p = 0;
    for (auto x : seq) sum_p += x;
    long long k_p = seq.size();

    long long sum_w = 0;
    for (auto x : powseq) sum_w += x;
    long long k_w = powseq.size();

    // Compare V using __int128
    __int128 vp = (__int128)k_p * sum_p;
    __int128 vw = (__int128)k_w * sum_w;

    vector<long long> chosen;
    if (vp >= vw) {
        chosen = seq;
    } else {
        chosen = powseq;
    }

    // Output
    cout << chosen.size() << endl;
    for (size_t i = 0; i < chosen.size(); ++i) {
        if (i > 0) cout << " ";
        cout << chosen[i];
    }
    cout << endl;

    return 0;
}