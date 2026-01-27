#include <bits/stdc++.h>
using namespace std;

using u128 = __uint128_t;
using u64 = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if(!(cin >> T)) return 0;

    auto ask = [&](unsigned long long Q)->unsigned long long{
        cout << "0 " << Q << "\n";
        cout.flush();
        unsigned long long g;
        if(!(cin >> g)) exit(0);
        return g;
    };

    // Sieve primes up to 1000
    const int LIM = 1000;
    vector<int> primes;
    vector<bool> is_prime(LIM + 1, true);
    is_prime[0] = is_prime[1] = false;
    for(int i=2;i<=LIM;i++){
        if(is_prime[i]){
            primes.push_back(i);
            if(1LL*i*i <= LIM){
                for(int j=i*i;j<=LIM;j+=i) is_prime[j] = false;
            }
        }
    }

    for(int t=0;t<T;t++){
        vector<int> cand;
        // Batch primes into products <= 1e18
        u128 prod = 1;
        vector<int> batch;
        const unsigned long long MAXQ = (unsigned long long)1e18;

        auto process_batch = [&](){
            if(batch.empty()) return;
            // Build Q
            u128 P = 1;
            for(int p: batch){
                P *= (u128)p;
            }
            unsigned long long Q = (unsigned long long)P;
            unsigned long long r = ask(Q);
            for(int p: batch){
                if(r % (unsigned long long)p == 0ULL) cand.push_back(p);
            }
            batch.clear();
            prod = 1;
        };

        for(int p: primes){
            if((u128)prod * (u128)p > (u128)MAXQ){
                process_batch();
            }
            prod *= (u128)p;
            batch.push_back(p);
        }
        process_batch();

        // For each candidate prime, determine exponent
        unsigned long long ansSmall = 1;
        for(int p: cand){
            // Compute max power of p <= 1e18
            u128 pk = 1;
            while(pk * (u128)p <= (u128)MAXQ) pk *= (u128)p;
            unsigned long long Q = (unsigned long long)pk;
            unsigned long long r = ask(Q);
            int exp = 0;
            while(r % (unsigned long long)p == 0ULL){
                r /= (unsigned long long)p;
                exp++;
            }
            ansSmall *= (unsigned long long)(exp + 1);
        }

        unsigned long long finalAns = ansSmall * 2ULL;
        if(finalAns == 0) finalAns = 1; // safety

        cout << "1 " << finalAns << "\n";
        cout.flush();
        // No input expected after answer before next game
    }

    return 0;
}