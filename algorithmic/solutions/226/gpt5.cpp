#include <bits/stdc++.h>
using namespace std;

static inline long long gcdll(long long a, long long b) {
    while (b) { long long t = a % b; a = b; b = t; }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n, x, y;
    if (!(cin >> n >> x >> y)) {
        return 0;
    }
    long long g = gcdll(x, y);
    long long a = x / g;
    long long b = y / g;
    if (a > b) swap(a, b);
    long long p_ll = a + b; // period length
    int p = (int)p_ll;

    // Build one period pattern (maximum independent set on the cycle of length p with step a)
    // Enumerate vertices in cycle order by adding a modulo p.
    // Select every other vertex, skipping the last if p is odd (i.e., select k even with k < p-1).
    vector<unsigned char> period(p, 0);
    long long cur = 0;
    for (int k = 0; k < p; ++k) {
        if ((k % 2 == 0) && (k < p - 1)) {
            period[(int)cur] = 1;
        }
        cur += a;
        if (cur >= p_ll) cur -= p_ll;
    }

    // Ones per full period
    int M = 0;
    for (int i = 0; i < p; ++i) M += period[i];

    auto max_window = [&](int r)->int {
        if (r <= 0) return 0;
        // initial sum for window [0, r-1]
        int s = 0;
        for (int i = 0; i < r; ++i) s += period[i % p];
        int best = s;
        for (int start = 1; start < p; ++start) {
            s += period[(start + r - 1) % p];
            s -= period[(start - 1) % p];
            if (s > best) best = s;
        }
        return best;
    };

    // Compute per-class best using periodic pattern for lengths q and q+1
    long long q = n / g;
    long long rem_classes = n % g; // number of residue classes with length q+1
    long long L1 = q;
    long long L2 = q + 1;

    auto solve_len = [&](long long L)->long long {
        if (L <= 0) return 0LL;
        long long k = L / p;
        int r = (int)(L % p);
        int w = max_window(r);
        return k * (long long)M + (long long)w;
    };

    long long val1 = solve_len(L1);
    long long val2 = solve_len(L2);

    long long ans = (g - rem_classes) * val1 + rem_classes * val2;
    cout << ans << "\n";
    return 0;
}