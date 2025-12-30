#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    if (n == 0) { // though n >=1
        cout << 1 << endl << 1 << endl;
        return 0;
    }

    // Power of 2 sequence
    vector<long long> powseq;
    long long cur = 1;
    powseq.push_back(1);
    while (true) {
        long long nextv = cur * 2;
        if (nextv > n) break;
        powseq.push_back(nextv);
        cur = nextv;
    }
    int kp = powseq.size();
    long long maxp = (kp == 0 ? 1 : powseq.back());
    long long sp = n / maxp;
    long long sum_p = 0;
    for (auto x : powseq) {
        sum_p += x * sp;
    }
    double v_p = (double) kp * sum_p;

    // Prime sequence
    const int MAXP = 2000000;
    vector<char> is_prime(MAXP + 1, 1);
    is_prime[0] = is_prime[1] = 0;
    for (long long i = 2; i * i <= MAXP; ++i) {
        if (is_prime[i]) {
            for (long long j = i * i; j <= MAXP; j += i) {
                is_prime[j] = 0;
            }
        }
    }
    vector<long long> primes;
    for (int i = 2; i <= MAXP; ++i) {
        if (is_prime[i]) primes.push_back(i);
    }

    vector<long long> seq;
    seq.push_back(1);
    if (n >= 2) seq.push_back(2);
    size_t ip = 1; // start from primes[1]=3
    while (ip + 1 < primes.size()) {
        long long p1 = primes[ip];
        long long p2 = primes[ip + 1];
        __int128 nextv = (__int128) p1 * p2;
        if (nextv > n) break;
        seq.push_back((long long) nextv);
        ++ip;
    }
    int ks = seq.size();
    long long maxs = (ks == 0 ? 1 : seq.back());
    long long ss = n / maxs;
    long long sum_s = 0;
    for (auto x : seq) {
        sum_s += x * ss;
    }
    double v_s = (double) ks * sum_s;

    // Choose the one with larger V
    bool choose_prime = (v_s > v_p);
    if (choose_prime) {
        cout << ks << endl;
        for (size_t i = 0; i < seq.size(); ++i) {
            cout << (seq[i] * ss);
            if (i + 1 < seq.size()) cout << " ";
            else cout << endl;
        }
    } else {
        cout << kp << endl;
        for (size_t i = 0; i < powseq.size(); ++i) {
            cout << (powseq[i] * sp);
            if (i + 1 < powseq.size()) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}