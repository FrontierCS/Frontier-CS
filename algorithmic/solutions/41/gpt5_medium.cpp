#include <bits/stdc++.h>
using namespace std;

static inline unsigned long long gcd_ull(unsigned long long a, unsigned long long b){
    return std::gcd(a,b);
}

static inline unsigned long long pow2_ull(int e){
    return (e >= 0) ? (1ULL << e) : 1ULL;
}

static inline int floor_log2_ull(unsigned long long x){
    return 63 - __builtin_clzll(x);
}

vector<unsigned long long> buildSequence(unsigned long long n, long long k){
    // k >= 2 expected
    vector<long long> t(k+1, 0); // 1-indexed
    auto bound = [&](int i)->unsigned long long{
        if(i == 1) return n;
        if(i == (int)k) return n / pow2_ull((int)k - 2);
        return n / pow2_ull(i - 1);
    };

    // t_k
    t[k] = (long long)bound((int)k);
    if(t[k] < 1) return {};

    // t_{k-1} if applicable
    if(k - 1 >= 2){
        unsigned long long B = bound((int)k - 1);
        long long lim = (long long)min<unsigned long long>(B, (t[k] - 1 >= 0 ? (unsigned long long)(t[k]-1) : 0ULL));
        if(lim < 1) return {};
        long long x = lim;
        if((x & 1LL) == 0) x--; // must be odd
        while(x >= 1 && gcd_ull((unsigned long long)x, (unsigned long long)t[k]) != 1ULL) x -= 2;
        if(x < 1) return {};
        t[k-1] = x;
    }

    // t_i for i = k-2 .. 2 (odd, coprime with next, <= min(B_i, 2*t_{i+1}-1))
    for(long long i = k - 2; i >= 2; --i){
        unsigned long long B = bound((int)i);
        __int128 two_next_minus1 = ( (__int128)2 * ( (__int128)t[i+1]) - 1 );
        unsigned long long limC = (two_next_minus1 > (__int128)LLONG_MAX ? ULLONG_MAX : (unsigned long long)max<__int128>(two_next_minus1, 0));
        unsigned long long limU = min<unsigned long long>(B, limC);
        if(limU < 1ULL) return {};
        long long x = (long long)limU;
        if((x & 1LL) == 0) x--; // odd
        while(x >= 1 && gcd_ull((unsigned long long)x, (unsigned long long)t[i+1]) != 1ULL) x -= 2;
        if(x < 1) return {};
        t[i] = x;
    }

    // t_1: odd, coprime with t2, <= min(n, 2*t2-1)
    {
        __int128 two_t2_minus1 = ( (__int128)2 * ( (__int128)t[2]) - 1 );
        unsigned long long limC = (two_t2_minus1 > (__int128)LLONG_MAX ? ULLONG_MAX : (unsigned long long)max<__int128>(two_t2_minus1, 0));
        unsigned long long limU = min<unsigned long long>(n, limC);
        if(limU < 1ULL) return {};
        long long x = (long long)limU;
        if((x & 1LL) == 0) x--; // odd
        while(x >= 1 && gcd_ull((unsigned long long)x, (unsigned long long)t[2]) != 1ULL) x -= 2;
        if(x < 1) return {};
        t[1] = x;
    }

    // Build sequence a
    vector<unsigned long long> a;
    a.reserve(k);
    a.push_back((unsigned long long)t[1]);
    if(a[0] < 1 || a[0] > n) return {};

    if(k >= 3){
        for(long long i = 2; i <= k-1; ++i){
            unsigned long long den = pow2_ull((int)i - 1);
            unsigned long long val = den * (unsigned long long)t[i];
            if(val < 1 || val > n) return {};
            a.push_back(val);
        }
        // last
        unsigned long long den = pow2_ull((int)k - 2);
        unsigned long long val = den * (unsigned long long)t[k];
        if(val < 1 || val > n) return {};
        a.push_back(val);
    } else { // k == 2 handled here
        // last
        unsigned long long val = (unsigned long long)t[2]; // no constraint for power of two here
        if(val < 1 || val > n) return {};
        a.push_back(val);
    }

    // Validate strictly increasing
    for(size_t i = 1; i < a.size(); ++i){
        if(!(a[i] > a[i-1])) return {};
    }
    // Validate gcd strictly increasing from i=3
    if(a.size() >= 3){
        unsigned long long prev_g = gcd_ull(a[1], a[0]);
        for(size_t i = 2; i < a.size(); ++i){
            unsigned long long g = gcd_ull(a[i], a[i-1]);
            if(!(g > prev_g)) return {};
            prev_g = g;
        }
    }
    return a;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned long long n;
    if(!(cin >> n)) return 0;

    if(n == 1ULL){
        cout << 1 << "\n1\n";
        return 0;
    }

    int m = floor_log2_ull(n);
    long long kmax = (long long)m + 2;

    for(long long k = kmax; k >= 2; --k){
        // quick feasibility: require 2^{k-2} <= n
        if(pow2_ull((int)k - 2) > n) continue;
        auto seq = buildSequence(n, k);
        if(!seq.empty()){
            // Try to append n if possible (increase gcd again)
            if(seq.back() < n && seq.size() >= 2){
                unsigned long long last_g = gcd_ull(seq[seq.size()-1], seq[seq.size()-2]);
                unsigned long long g2 = gcd_ull(n, seq.back());
                if(g2 > last_g && n > seq.back()){
                    seq.push_back(n);
                }
            }

            cout << seq.size() << "\n";
            for(size_t i = 0; i < seq.size(); ++i){
                if(i) cout << ' ';
                cout << seq[i];
            }
            cout << "\n";
            return 0;
        }
    }

    // Fallback k=1
    cout << 1 << "\n" << n << "\n";
    return 0;
}