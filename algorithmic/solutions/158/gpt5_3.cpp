#include <bits/stdc++.h>
using namespace std;

using ll = long long;

ll extgcd_pos(ll a, ll b, ll &x, ll &y) {
    if (b == 0) {
        x = 1;
        y = 0;
        return a;
    }
    ll x1, y1;
    ll g = extgcd_pos(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    vector<pair<int,int>> pts(N);
    long long seedmix = 146527;
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
        pts[i] = {x, y};
        seedmix ^= (uint64_t(x) + 1000003ULL * (uint64_t(y) + 1000003ULL * (i + 1)));
        seedmix *= 1000003ULL;
    }
    // RNG
    uint64_t seed = 88172645463393265ull ^ (uint64_t)N * 1000003ull ^ (uint64_t)K * 91138233ull ^ (uint64_t)seedmix;
    auto rng = [&seed]() -> uint64_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        return seed;
    };
    auto randi = [&](ll L, ll R) -> ll {
        return L + (ll)(rng() % (uint64_t)(R - L + 1));
    };
    
    const int R = 10000;
    const ll Tlimit = 100000; // keep coordinates well within 1e9
    int L = K;
    cout << L << '\n';
    for (int i = 0; i < L; ++i) {
        // choose direction vector
        ll vx = 0, vy = 0;
        // Mix some deterministic simple directions occasionally
        if (i % 25 == 0) { vx = 0; vy = 1; }              // vertical
        else if (i % 25 == 1) { vx = 1; vy = 0; }         // horizontal
        else {
            do {
                vx = (ll)randi(-1000, 1000);
                vy = (ll)randi(-1000, 1000);
            } while (vx == 0 && vy == 0);
        }
        ll acoef = -vy, bcoef = vx;
        ll aa = llabs(acoef), bb = llabs(bcoef);
        ll x0, y0;
        ll g = extgcd_pos(aa, bb, x0, y0); // aa*x0 + bb*y0 = g
        // apply signs
        if (acoef < 0) x0 = -x0;
        if (bcoef < 0) y0 = -y0;
        if (g == 0) { // shouldn't happen
            cout << "0 0 1 0\n";
            continue;
        }
        long double len = sqrt((long double)vx * (long double)vx + (long double)vy * (long double)vy);
        if (len == 0) len = 1;
        ll tmax_len = (ll)floor((long double)R * len / (long double)g);
        ll tmax = min((ll)Tlimit, tmax_len);
        if (tmax <= 0) tmax = 1;
        ll t = randi(-tmax, tmax);
        if (t == 0) t = 1;
        ll s_over_g = t; // since s = t*g
        ll px = x0 * s_over_g;
        ll py = y0 * s_over_g;
        ll vx_step = vx / g;
        ll vy_step = vy / g;
        // Ensure within bounds (they already are, but clamp if needed by shifting along the line)
        auto clamp_to_bounds = [&](ll &X, ll &Y) {
            // Try shifting by k steps along the line if out of bounds
            // Solve to bring X,Y within [-1e9, 1e9] approximately.
            const ll BND = 1000000000LL;
            if (vx_step == 0 && vy_step == 0) return;
            // Try limited adjustments
            for (int tries = 0; tries < 5; ++tries) {
                if (X >= -BND && X <= BND && Y >= -BND && Y <= BND) break;
                ll kx = 0, ky = 0;
                if (vx_step != 0) {
                    if (X < -BND) kx = ((-BND - X) / vx_step) + ((vx_step > 0) ? 1 : -1);
                    else if (X > BND) kx = ((BND - X) / vx_step) + ((vx_step < 0) ? 1 : -1);
                }
                if (vy_step != 0) {
                    if (Y < -BND) ky = ((-BND - Y) / vy_step) + ((vy_step > 0) ? 1 : -1);
                    else if (Y > BND) ky = ((BND - Y) / vy_step) + ((vy_step < 0) ? 1 : -1);
                }
                ll k = 0;
                if (vx_step != 0 && vy_step != 0) k = (ll)((kx + ky) / 2);
                else if (vx_step != 0) k = kx;
                else if (vy_step != 0) k = ky;
                if (k == 0) k = (vx_step != 0 ? ((X > BND) ? -1 : 1) : ((Y > BND) ? -1 : 1));
                X += vx_step * k;
                Y += vy_step * k;
            }
        };
        clamp_to_bounds(px, py);
        ll qx = px + vx_step;
        ll qy = py + vy_step;
        // If somehow identical (shouldn't), adjust
        if (px == qx && py == qy) {
            qx += (vy_step == 0 ? 1 : vy_step);
            qy -= (vx_step == 0 ? 1 : vx_step);
        }
        cout << px << ' ' << py << ' ' << qx << ' ' << qy << '\n';
    }
    return 0;
}