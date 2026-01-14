#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ull = unsigned long long;
using lll = __int128;

ll modpow(ll base, ll exp, ll mod) {
    ll res = 1;
    base %= mod;
    if (base < 0) base += mod;
    while (exp > 0) {
        if (exp & 1) res = (lll)res * base % mod;
        base = (lll)base * base % mod;
        exp >>= 1;
    }
    return res;
}

ll mod_inverse(ll a, ll m) {
    return modpow(a, m - 2, m);
}

ll crt(ll x1, ll m1, ll x2, ll m2, ll n) {
    ll g = __gcd(m1, m2);
    if ((x1 - x2) % g != 0) assert(false);
    ll inv = mod_inverse(m2 % m1, m1);
    ll u = ((x1 - x2) % m1 + m1) % m1 * inv % m1;
    return (x2 + (lll)m2 * u) % n;
}

vector<ll> factor(ll x) {
    vector<ll> fac;
    for (ll i = 2; i * i <= x; ++i) {
        if (x % i == 0) {
            fac.push_back(i);
            while (x % i == 0) x /= i;
        }
    }
    if (x > 1) fac.push_back(x);
    return fac;
}

ll find_primroot(ll pr) {
    auto facs = factor(pr - 1);
    for (ll g = 2; g < pr; ++g) {
        bool ok = true;
        for (auto f : facs) {
            if (modpow(g, (pr - 1) / f, pr) == 1) {
                ok = false;
                break;
            }
        }
        if (ok) return g;
    }
    return -1;
}

int get_bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ull n;
    cin >> n;
    lll NN = n;

    // factor n
    ll sqrt_n = sqrt(n) + 10;
    ll pp = -1, qq = -1;
    for (ll d = (1LL << 29) | 1; d <= sqrt_n; d += 2) {
        if (n % d == 0) {
            pp = d;
            qq = n / d;
            break;
        }
    }
    if (pp == -1) {
        // try from high
        for (ll d = (1LL << 30) - 2; d >= (1LL << 29); d -= 2) {
            if (n % d == 0) {
                pp = d;
                qq = n / d;
                break;
            }
        }
    }
    if (pp > qq) swap(pp, qq);
    ll p = pp, q = qq;

    // popcount query
    cout << "? 0" << endl;
    fflush(stdout);
    ll T0;
    cin >> T0;
    ll s = T0 - 61;

    // compute vp, vq
    int vp = 0;
    ll temp = p - 1;
    while (temp % 2 == 0) {
        temp /= 2;
        vp++;
    }
    int vq = 0;
    temp = q - 1;
    while (temp % 2 == 0) {
        temp /= 2;
        vq++;
    }
    int vmax = max(vp, vq);

    // prim roots
    ll primp = find_primroot(p);
    ll primq = find_primroot(q);

    // now build D
    ull D = 0;
    int cur_pos = 0;
    int cur_pop = 0;
    int chunk_size = 15;  // safe

    while (cur_pos < 60) {
        int rem = 60 - cur_pos;
        int ch_sz = min(chunk_size, rem);

        // create a with target_v = min(ch_sz, vmax)
        int target_v = min(ch_sz, vmax);

        // determine large comp
        ll large_c = (vp >= vq ? p : q);
        int large_vv = (vp >= vq ? vp : vq);
        ll small_c = (vp >= vq ? q : p);
        int small_vv = (vp >= vq ? vq : vp);
        ll prim_large = (vp >= vq ? primp : primq);

        ll gs_large = modpow(prim_large, (large_c - 1) / (1LL << large_vv), large_c);
        ll gs_n = crt(gs_large, large_c, 1LL, small_c, n);
        ull this_a = modpow(gs_n, (1LL << (large_vv - target_v)), n);

        // precompute AA
        vector<ull> AA(61, 0);
        AA[0] = this_a % n;
        for (int i = 0; i < 60; ++i) {
            lll sq = (lll)AA[i] * AA[i] % NN;
            AA[i + 1] = (ull)sq;
        }

        // fixed sq
        ll fixed_sq = 0;
        for (int i = 0; i < 60; ++i) {
            int b = get_bits(AA[i]);
            fixed_sq += 1LL * (b + 1) * (b + 1);
        }

        // query
        cout << "? " << AA[0] << endl;
        fflush(stdout);
        ll Tobs;
        cin >> Tobs;
        ll total_mult_obs = Tobs - fixed_sq;

        // now candidates
        vector<ull> cands;
        ull max_ee = 1ULL << ch_sz;
        for (ull ee = 0; ee < max_ee; ++ee) {
            int pop_ee = __builtin_popcountll(ee);
            lll rrr = 1;
            ll ff = 0;
            int sim_end = cur_pos + ch_sz - 1;
            for (int ii = 0; ii <= sim_end; ++ii) {
                ull brr = get_bits((ull)rrr);
                ull baa = get_bits(AA[ii]);
                bool isset;
                if (ii < cur_pos) {
                    isset = (D & (1ULL << ii)) != 0;
                } else {
                    int loc = ii - cur_pos;
                    isset = (ee & (1ULL << loc)) != 0;
                }
                if (isset) {
                    ff += (ll)(brr + 1) * (baa + 1);
                    rrr = (rrr * (lll)AA[ii]) % NN;
                }
            }
            ull br_after = get_bits((ull)rrr);
            ll cc = 2LL * (br_after + 1);
            ll j_high = (ll)s - cur_pop - pop_ee;
            if (j_high < 0 || j_high > 60 - (sim_end + 1)) continue;
            ll expct = ff + j_high * cc;
            if (expct == total_mult_obs) {
                cands.push_back(ee);
            }
        }

        // filter if needed
        int max_attempts = 20;
        int att = 0;
        while (cands.size() > 1 && att < max_attempts) {
            att++;
            int target_v2 = max(1, target_v - att);
            // create new this_a with target_v2
            ll gs_n2 = crt(gs_large, large_c, 1LL, small_c, n);
            ull this_a2 = modpow(gs_n2, (1LL << (large_vv - target_v2)), n);

            // precompute AA2
            vector<ull> AA2(61, 0);
            AA2[0] = this_a2 % n;
            for (int i = 0; i < 60; ++i) {
                lll sq = (lll)AA2[i] * AA2[i] % NN;
                AA2[i + 1] = (ull)sq;
            }

            ll fixed_sq2 = 0;
            for (int i = 0; i < 60; ++i) {
                int b = get_bits(AA2[i]);
                fixed_sq2 += 1LL * (b + 1) * (b + 1);
            }

            cout << "? " << AA2[0] << endl;
            fflush(stdout);
            ll Tobs2;
            cin >> Tobs2;
            ll total_mult_obs2 = Tobs2 - fixed_sq2;

            vector<ull> new_cands;
            for (auto ee : cands) {
                int pop_ee = __builtin_popcountll(ee);
                lll rrr = 1;
                ll ff = 0;
                int sim_end = cur_pos + ch_sz - 1;
                for (int ii = 0; ii <= sim_end; ++ii) {
                    ull brr = get_bits((ull)rrr);
                    ull baa = get_bits(AA2[ii]);
                    bool isset;
                    if (ii < cur_pos) {
                        isset = (D & (1ULL << ii)) != 0;
                    } else {
                        int loc = ii - cur_pos;
                        isset = (ee & (1ULL << loc)) != 0;
                    }
                    if (isset) {
                        ff += (ll)(brr + 1) * (baa + 1);
                        rrr = (rrr * (lll)AA2[ii]) % NN;
                    }
                }
                ull br_after = get_bits((ull)rrr);
                ll cc = 2LL * (br_after + 1);
                ll j_high = (ll)s - cur_pop - pop_ee;
                ll expct = ff + j_high * cc;
                if (expct == total_mult_obs2) {
                    new_cands.push_back(ee);
                }
            }
            cands = new_cands;
        }

        // assume now ==1
        assert(cands.size() == 1);
        ull the_ee = cands[0];
        D |= (the_ee << cur_pos);
        cur_pop += __builtin_popcountll(the_ee);
        cur_pos += ch_sz;
    }

    cout << "! " << D << endl;
    fflush(stdout);

    return 0;
}