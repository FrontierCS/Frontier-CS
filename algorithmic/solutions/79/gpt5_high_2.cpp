#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static inline int bits_u64(u64 x){
    if(x==0) return 0;
    return 64 - __builtin_clzll(x);
}

static inline u64 modmul(u64 a, u64 b, u64 mod){
    return (u64)((u128)a * (u128)b % (u128)mod);
}

static inline u64 cost_mul(u64 x, u64 y){
    // (bits(x)+1)*(bits(y)+1)
    return (u64)(bits_u64(x)+1) * (u64)(bits_u64(y)+1);
}

// SplitMix64 RNG
struct SplitMix64 {
    u64 x;
    SplitMix64(u64 seed=0x9e3779b97f4a7c15ull) { x = seed; }
    u64 next() {
        u64 z = (x += 0x9e3779b97f4a7c15ull);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
} rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    u64 n;
    if(!(cin >> n)) return 0;

    const int BITS = 60;
    const int MAXQ = 30000;
    int M = 12000;
    int STEP = 3000;
    if(M > MAXQ) M = MAXQ;

    vector<u64> A; A.reserve(MAXQ);
    vector<i64> T; T.reserve(MAXQ);
    vector<u64> baseT; baseT.reserve(MAXQ);
    vector<u64> S; S.reserve(MAXQ);

    // Preallocate storage for aPow and bit-lengths
    vector<u64> aPow((size_t)MAXQ * BITS);
    vector<unsigned char> aBits((size_t)MAXQ * BITS);

    auto precompute_entry = [&](int idx){
        u64 a = A[idx];
        u64 cur = a;
        u64 base = 0;
        for(int i=0;i<BITS;i++){
            size_t off = (size_t)idx*BITS + i;
            aPow[off] = cur;
            int bl = bits_u64(cur);
            aBits[off] = (unsigned char)bl;
            u64 c7 = (u64)(bl+1) * (u64)(bl+1);
            base += c7;
            cur = modmul(cur, cur, n);
        }
        baseT[idx] = base;
    };

    auto ask = [&](u64 a)->i64{
        cout << "? " << a << endl;
        cout.flush();
        i64 t; 
        if(!(cin >> t)) exit(0);
        return t;
    };

    auto add_queries = [&](int want){
        int cur = (int)A.size();
        int need = min(want, MAXQ - cur);
        for(int i=0;i<need;i++){
            u64 a = rng.next() % n;
            A.push_back(a);
            i64 t = ask(a);
            T.push_back(t);
            baseT.push_back(0);
            precompute_entry(cur+i);
        }
        // compute S = T - base
        int sz = (int)A.size();
        S.resize(sz);
        for(int i=cur;i<sz;i++){
            S[i] = T[i] - (i64)baseT[i];
        }
    };

    auto decode_with_M = [&](int useM)->u64{
        vector<u64> r(useM, 1);
        vector<u64> csum(useM, 0);
        u64 d = 0;

        for(int i=0;i<BITS;i++){
            // compute X and Y stats
            __int128 sumX = 0, sumY = 0, sumXX = 0, sumXY = 0;
            for(int k=0;k<useM;k++){
                size_t off = (size_t)k*BITS + i;
                u64 ai = aPow[off];
                u64 X = (u64)(bits_u64(r[k])+1) * (u64)(aBits[off]+1);
                i64 Y = (i64)((S[k] >= csum[k]) ? (S[k] - csum[k]) : 0); // non-negative by design
                sumX += X;
                sumY += Y;
                sumXX += (u128)X * (u128)X;
                sumXY += (u128)X * (u128)Y;
            }
            long double Mld = (long double)useM;
            long double sx = (long double)(u64)sumX;
            long double sy = (long double)(i64)sumY;
            long double sxx = (long double)(u64)sumXX;
            long double sxy = (long double)(u64)sumXY;

            long double cov = sxy - (sx*sy)/Mld;
            long double varx = sxx - (sx*sx)/Mld;

            int bit = 0;
            if(varx > 0){
                long double slope = cov / varx;
                // Threshold around 0.5; adjust softly
                if(slope > 0.5L) bit = 1;
                else bit = 0;
            }else{
                // if varx is zero (unlikely), fallback based on cov sign
                if(cov > 0) bit = 1; else bit = 0;
            }

            if(bit) d |= (1ULL << i);

            // update r and csum
            for(int k=0;k<useM;k++){
                size_t off = (size_t)k*BITS + i;
                if(bit){
                    u64 ai = aPow[off];
                    u64 X = (u64)(bits_u64(r[k])+1) * (u64)(aBits[off]+1);
                    csum[k] += X;
                    r[k] = modmul(r[k], ai, n);
                }
            }
        }
        return d;
    };

    auto predict_time = [&](int idx, u64 dval)->i64{
        u64 r = 1;
        i64 tot = 0;
        for(int i=0;i<BITS;i++){
            size_t off = (size_t)idx*BITS + i;
            u64 ai = aPow[off];
            int bl = aBits[off];
            tot += (i64)((u64)(bl+1) * (u64)(bl+1));
            if((dval >> i) & 1ULL){
                tot += (i64)((u64)(bits_u64(r)+1) * (u64)(bl+1));
                r = modmul(r, ai, n);
            }
        }
        return tot;
    };

    // Initial batch
    add_queries(M);

    u64 d = 0;
    while(true){
        d = decode_with_M((int)A.size());
        bool ok = true;
        for(int i=0;i<(int)A.size();i++){
            i64 pred = predict_time(i, d);
            if(pred != T[i]){
                ok = false;
                break;
            }
        }
        if(ok){
            cout << "! " << d << endl;
            cout.flush();
            return 0;
        }
        // Need more data
        int cur = (int)A.size();
        if(cur >= MAXQ) {
            // Give best guess anyway
            cout << "! " << d << endl;
            cout.flush();
            return 0;
        }
        int add = min(STEP, MAXQ - cur);
        add_queries(add);
    }
}