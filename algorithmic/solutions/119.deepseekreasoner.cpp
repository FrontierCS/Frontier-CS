#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const ll MOD = 1e9 + 7;
const ll G = 5;                // primitive root modulo MOD
const int CHUNK_SIZE = 29;     // 2^29 < MOD-1
const int BS_SIZE = 1 << 15;   // 32768, for baby-step giant-step

ll modpow(ll a, ll e) {
    ll res = 1;
    while (e) {
        if (e & 1) res = res * a % MOD;
        a = a * a % MOD;
        e >>= 1;
    }
    return res;
}

ll modinv(ll a) {
    return modpow(a, MOD - 2);
}

vector<ll> g_pow2;            // G^(2^i) mod MOD
unordered_map<ll, int> bs_map; // baby steps: value -> exponent
ll invG_m;                    // G^(-BS_SIZE) mod MOD

void precompute() {
    // precompute G^(2^i) for i = 0..28
    g_pow2.resize(30);
    g_pow2[0] = G;
    for (int i = 1; i < 30; ++i)
        g_pow2[i] = g_pow2[i - 1] * g_pow2[i - 1] % MOD;

    // baby steps: G^i for i = 0..BS_SIZE-1
    ll cur = 1;
    for (int i = 0; i < BS_SIZE; ++i) {
        bs_map[cur] = i;
        cur = cur * G % MOD;
    }

    // precompute G^(-BS_SIZE)
    ll invG = modinv(G);
    invG_m = modpow(invG, BS_SIZE);
}

// discrete log of c = G^mask, with mask in [0, 2^K)
ll dlog(ll c, int K) {
    ll max_mask = (1LL << K) - 1;
    ll cur = c;
    for (ll t = 0; t * BS_SIZE <= max_mask; ++t) {
        auto it = bs_map.find(cur);
        if (it != bs_map.end()) {
            ll mask = it->second + t * BS_SIZE;
            if (mask <= max_mask)
                return mask;
        }
        cur = cur * invG_m % MOD;
    }
    return -1; // should not happen
}

int main() {
    precompute();

    int n;
    cin >> n;
    vector<int> ops(n + 1, 0); // ops[1..n], 0: '+', 1: '*'

    int chunk_start = 1;
    while (chunk_start <= n) {
        int chunk_end = min(n, chunk_start + CHUNK_SIZE - 1);
        int K = chunk_end - chunk_start + 1;

        // prepare a[i] for i = 1..n
        vector<ll> a(n + 1, 1);
        for (int i = chunk_start; i <= chunk_end; ++i) {
            int idx = i - chunk_start;
            a[i] = g_pow2[idx];
        }

        // query with a0 = 1
        cout << "? " << 1;
        for (int i = 1; i <= n; ++i) cout << ' ' << a[i];
        cout << endl;
        fflush(stdout);
        ll res1;
        cin >> res1;

        // query with a0 = 2
        cout << "? " << 2;
        for (int i = 1; i <= n; ++i) cout << ' ' << a[i];
        cout << endl;
        fflush(stdout);
        ll res2;
        cin >> res2;

        // c = coefficient of a0
        ll c = (res2 - res1 + MOD) % MOD;

        // recover mask from c = G^mask
        ll mask = dlog(c, K);

        // decode mask to operators
        for (int j = 0; j < K; ++j) {
            if (mask & (1LL << j))
                ops[chunk_start + j] = 1;
            else
                ops[chunk_start + j] = 0;
        }

        chunk_start += CHUNK_SIZE;
    }

    // output answer
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << ' ' << ops[i];
    cout << endl;
    fflush(stdout);

    return 0;
}