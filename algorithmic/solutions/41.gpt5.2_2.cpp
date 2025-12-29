#include <bits/stdc++.h>
#include <charconv>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

struct Candidate {
    vector<int64> a;
    i128 V = -1;
};

static inline i128 calcV(const vector<int64>& a) {
    i128 sum = 0;
    for (int64 x : a) sum += (i128)x;
    return sum * (i128)a.size();
}

static inline i128 oddLastBase(int64 k) {
    // k >= 3
    i128 x = (i128)(2 * k - 3);
    i128 y = (i128)(2 * k - 4);
    return x * y;
}

static int64 maxOddK(int64 n) {
    if (n < 6) return 0;
    int64 lo = 3, hi = 1000000, best = 0;
    while (lo <= hi) {
        int64 mid = (lo + hi) >> 1;
        i128 val = oddLastBase(mid);
        if (val <= (i128)n) {
            best = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return best;
}

static Candidate buildOdd(int64 n) {
    Candidate cand;
    int64 k = maxOddK(n);
    if (k == 0) return cand;

    i128 baseLast = oddLastBase(k);
    int64 c = (int64)((i128)n / baseLast);
    if (c <= 0) return cand;

    vector<int64> a(k);

    // a2 = 3c, a1 = a2 - 1 for better sum while keeping gcd(a2,a1)=1
    a[1] = (int64)((i128)c * 3);
    a[0] = a[1] - 1;

    // middle terms
    for (int64 i = 3; i <= k - 1; i++) {
        i128 base = (i128)(2 * i - 3) * (i128)(2 * i - 1);
        a[i - 1] = (int64)((i128)c * base);
    }

    // maximize last term under constraints
    int64 d_prev = 2 * k - 5; // odd
    int64 dk = 2 * k - 3;     // odd
    i128 g = (i128)c * (i128)dk;

    int64 M = (int64)((i128)n / g);
    while (M > d_prev && std::gcd((int64)M, d_prev) != 1) --M;
    if (M <= d_prev) {
        // should not happen; fallback to base
        M = d_prev + 1;
    }
    a[k - 1] = (int64)(g * (i128)M);

    cand.a = std::move(a);
    cand.V = calcV(cand.a);
    return cand;
}

static Candidate buildBestPow2(int64 n) {
    Candidate best;

    // k = 3..62 (n <= 1e12 => actually <= 41), but safe
    for (int k = 3; k <= 62; k++) {
        i128 pow2 = (i128)1 << (k - 1); // 2^(k-1)
        if (pow2 > (i128)n) break;

        int64 c = (int64)((i128)n / pow2);
        if (c <= 0) break;

        vector<int64> a(k);
        a[1] = (int64)((i128)c * 2); // 2c
        a[0] = a[1] - 1;

        i128 cur = a[1];
        for (int pos = 2; pos <= k - 2; pos++) {
            cur *= 2;
            a[pos] = (int64)cur;
        }

        int64 prev = a[k - 2];
        int64 mult = (int64)(n / prev);
        if (mult < 2) continue; // would violate strict increase
        a[k - 1] = prev * mult; // maximize last while preserving gcd = prev

        Candidate cand;
        cand.a = std::move(a);
        cand.V = calcV(cand.a);
        if (cand.V > best.V) best = std::move(cand);
    }
    return best;
}

static Candidate buildPair(int64 n) {
    Candidate cand;
    if (n < 2) return cand;
    cand.a = {n - 1, n};
    cand.V = calcV(cand.a);
    return cand;
}

static Candidate buildSingle(int64 n) {
    Candidate cand;
    cand.a = {n};
    cand.V = calcV(cand.a);
    return cand;
}

static inline void appendLL(string& s, int64 x) {
    char buf[32];
    auto [ptr, ec] = to_chars(buf, buf + sizeof(buf), x);
    (void)ec;
    s.append(buf, ptr);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int64 n;
    if (!(cin >> n)) return 0;

    Candidate best = buildSingle(n);

    {
        Candidate cand = buildPair(n);
        if (cand.V > best.V) best = std::move(cand);
    }
    {
        Candidate cand = buildBestPow2(n);
        if (cand.V > best.V) best = std::move(cand);
    }
    {
        Candidate cand = buildOdd(n);
        if (cand.V > best.V) best = std::move(cand);
    }

    const auto& a = best.a;
    int64 k = (int64)a.size();

    string out;
    out.reserve((size_t)k * 16 + 64);
    appendLL(out, k);
    out.push_back('\n');
    for (int64 i = 0; i < k; i++) {
        if (i) out.push_back(' ');
        appendLL(out, a[i]);
    }
    out.push_back('\n');

    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}