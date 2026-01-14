#include <bits/stdc++.h>

#if (defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86))
  #include <immintrin.h>
#endif

using namespace std;

static inline int isqrt_ll(long long x) {
    int r = (int)floor(sqrt((long double)x));
    while (1LL * (r + 1) * (r + 1) <= x) ++r;
    while (1LL * r * r > x) --r;
    return r;
}

static inline int maxk_len(int n) {
    long double v = sqrt((long double)1 + 4.0L * (long double)n);
    long long k = (long long)floor((v - 1.0L) / 2.0L);
    while (1LL * (k + 1) * (k + 2) <= n) ++k;
    while (1LL * k * (k + 1) > n) --k;
    return (int)k;
}

static inline long long count_for_k(const int* pref, int n, int k, int L) {
    const size_t cnt = (size_t)n - (size_t)L + 1;
    const int* p1 = pref;
    const int* p2 = pref + L;
    long long ans = 0;

#if defined(__AVX2__)
    const __m256i kv = _mm256_set1_epi32(k);
    size_t i = 0;
    for (; i + 8 <= cnt; i += 8) {
        __m256i a = _mm256_loadu_si256((const __m256i*)(p1 + i));
        __m256i b = _mm256_loadu_si256((const __m256i*)(p2 + i));
        __m256i d = _mm256_sub_epi32(b, a);
        __m256i c = _mm256_cmpeq_epi32(d, kv);
        int mask = _mm256_movemask_ps(_mm256_castsi256_ps(c));
        ans += __builtin_popcount((unsigned)mask);
    }
    for (; i < cnt; ++i) ans += (p2[i] - p1[i] == k);
    return ans;
#elif defined(__SSE2__)
    const __m128i kv = _mm_set1_epi32(k);
    size_t i = 0;
    for (; i + 4 <= cnt; i += 4) {
        __m128i a = _mm_loadu_si128((const __m128i*)(p1 + i));
        __m128i b = _mm_loadu_si128((const __m128i*)(p2 + i));
        __m128i d = _mm_sub_epi32(b, a);
        __m128i c = _mm_cmpeq_epi32(d, kv);
        int mask = _mm_movemask_ps(_mm_castsi128_ps(c));
        ans += __builtin_popcount((unsigned)mask);
    }
    for (; i < cnt; ++i) ans += (p2[i] - p1[i] == k);
    return ans;
#else
    size_t i = 0;
    unsigned long long a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    for (; i + 4 <= cnt; i += 4) {
        a0 += (p2[i] - p1[i] == k);
        a1 += (p2[i + 1] - p1[i + 1] == k);
        a2 += (p2[i + 2] - p1[i + 2] == k);
        a3 += (p2[i + 3] - p1[i + 3] == k);
    }
    ans += (long long)(a0 + a1 + a2 + a3);
    for (; i < cnt; ++i) ans += (p2[i] - p1[i] == k);
    return ans;
#endif
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    cin >> s;
    const int n = (int)s.size();
    vector<int> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) pref[i + 1] = pref[i] + (s[i] == '1');

    const int ones = pref[n];
    const int zeros = n - ones;

    int kmax = maxk_len(n);
    kmax = min(kmax, ones);
    kmax = min(kmax, isqrt_ll(zeros));

    long long ans = 0;
    const int* p = pref.data();

    for (int k = 1; k <= kmax; ++k) {
        int L = k * (k + 1);
        if (L > n) break;
        ans += count_for_k(p, n, k, L);
    }

    cout << ans << "\n";
    return 0;
}