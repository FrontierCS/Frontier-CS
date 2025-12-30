#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

struct CRTState {
    int64 r = 0;   // current remainder
    int64 m = 1;   // current modulus
    bool valid = true;
};

int64 extgcd(int64 a, int64 b, int64 &x, int64 &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    int64 x1, y1;
    int64 g = extgcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

void crt_add(CRTState &st, int64 a, int64 mod) {
    if (!st.valid) return;
    int64 x, y;
    int64 g = extgcd(st.m, mod, x, y);
    int64 diff = a - st.r;
    if ((diff % g + g) % g != 0) { st.valid = false; return; }
    int64 lcm = st.m / g * mod;
    int64 t = (diff / g) % (mod / g);
    if (t < 0) t += (mod / g);
    int64 k = (int64)((i128)t * x % (mod / g));
    if (k < 0) k += (mod / g);
    st.r = (st.r + (i128)st.m * k) % lcm;
    if (st.r < 0) st.r += lcm;
    st.m = lcm;
}

static inline long long isqrtll(long long x) {
    long double d = sqrt((long double)x);
    long long r = (long long)(d + 0.5L);
    while (r*r > x) --r;
    while ((r+1)*(r+1) <= x) ++r;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    vector<int> moduli = {16, 3, 5, 7, 11, 13, 17};
    int total_queries = 0;
    for (int m : moduli) total_queries += m;

    // Send robots: one query per residue class of each modulus
    for (int m : moduli) {
        for (int r = 0; r < m; ++r) {
            vector<int> v;
            int start = (r == 0 ? m : r);
            for (int x = start; x <= 1000; x += m) v.push_back(x);
            cout << "? " << v.size();
            for (int x : v) cout << " " << x;
            cout << "\n";
            cout.flush();
        }
    }

    // Get results
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Decode S = a+b and T = a*b via CRT on per-modulus sums/products of residues
    CRTState crtS, crtT;
    int idx = 0;
    for (int m : moduli) {
        vector<int> res;
        for (int r = 0; r < m; ++r) {
            if (idx < (int)ans.size() && ans[idx]) res.push_back(r);
            ++idx;
        }
        int64 s_mod = 0, t_mod = 0;
        if (res.size() == 1) {
            int64 r = res[0];
            s_mod = (2 * r) % m;
            t_mod = (r * r) % m;
        } else if (res.size() == 2) {
            int64 r1 = res[0], r2 = res[1];
            s_mod = (r1 + r2) % m;
            t_mod = (r1 * r2) % m;
        } else {
            // Should not happen; fallback to avoid crash
            s_mod = 0;
            t_mod = 0;
        }
        crt_add(crtS, s_mod, m);
        crt_add(crtT, t_mod, m);
    }

    int64 S = crtS.r;
    int64 T = crtT.r;

    // Solve x^2 - Sx + T = 0 -> roots a,b
    int64 D = S*S - 4*T;
    int64 sq = isqrtll(D);
    int64 a = (S - sq) / 2;
    int64 b = (S + sq) / 2;

    cout << "! " << a << " " << b << "\n";
    cout.flush();

    return 0;
}