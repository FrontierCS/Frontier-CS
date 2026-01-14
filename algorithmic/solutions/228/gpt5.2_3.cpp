#include <bits/stdc++.h>
using namespace std;

#if defined(__AVX2__) || defined(__SSE2__)
  #include <immintrin.h>
#endif

#if defined(__ARM_NEON)
  #include <arm_neon.h>
#endif

static inline long long isqrtll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long) sqrtl((long double)x);
    while ((r + 1) > 0 && (r + 1) * (r + 1) <= x) ++r;
    while (r * r > x) --r;
    return r;
}

static inline unsigned long long count_for_t(const int* pref, int n, int t) {
    long long Lll = 1LL * t * (t + 1);
    if (Lll > n) return 0;
    int L = (int)Lll;

    int len = n - L + 1; // number of windows
    const int* p = pref;
    const int* q = pref + L;

    unsigned long long cnt = 0;
    int i = 0;

#if defined(__AVX2__)
    __m256i tv = _mm256_set1_epi32(t);
    for (; i + 8 <= len; i += 8) {
        __m256i a = _mm256_loadu_si256((const __m256i*)(p + i));
        __m256i b = _mm256_loadu_si256((const __m256i*)(q + i));
        __m256i ap = _mm256_add_epi32(a, tv);
        __m256i eq = _mm256_cmpeq_epi32(ap, b);
        int mask = _mm256_movemask_ps(_mm256_castsi256_ps(eq));
        cnt += (unsigned)__builtin_popcount((unsigned)mask);
    }
#elif defined(__SSE2__)
    __m128i tv = _mm_set1_epi32(t);
    for (; i + 4 <= len; i += 4) {
        __m128i a = _mm_loadu_si128((const __m128i*)(p + i));
        __m128i b = _mm_loadu_si128((const __m128i*)(q + i));
        __m128i ap = _mm_add_epi32(a, tv);
        __m128i eq = _mm_cmpeq_epi32(ap, b);
        int mask = _mm_movemask_ps(_mm_castsi128_ps(eq));
        cnt += (unsigned)__builtin_popcount((unsigned)mask);
    }
#elif defined(__ARM_NEON)
    int32x4_t tv = vdupq_n_s32(t);
    for (; i + 4 <= len; i += 4) {
        int32x4_t a = vld1q_s32(p + i);
        int32x4_t b = vld1q_s32(q + i);
        int32x4_t ap = vaddq_s32(a, tv);
        uint32x4_t eq = vceqq_s32(ap, b);
        // Convert 0xFFFFFFFF -> 1, 0x00000000 -> 0 by shifting right 31
        uint32x4_t ones = vshrq_n_u32(eq, 31);
        #if defined(__aarch64__)
            cnt += (unsigned long long) vaddvq_u32(ones);
        #else
            uint32_t tmp[4];
            vst1q_u32(tmp, ones);
            cnt += (unsigned long long)tmp[0] + tmp[1] + tmp[2] + tmp[3];
        #endif
    }
#endif

    for (; i < len; ++i) {
        if (q[i] == p[i] + t) ++cnt;
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) {
        cout << 0 << "\n";
        return 0;
    }
    int n = (int)s.size();
    vector<int> pref(n + 1, 0);
    int zeros = 0;
    for (int i = 0; i < n; ++i) {
        pref[i + 1] = pref[i] + (s[i] == '1');
        zeros += (s[i] == '0');
    }
    int ones = n - zeros;

    long long disc = 1LL + 4LL * n;
    long long root = isqrtll(disc);
    long long K1 = (root - 1) / 2;             // max t with t^2 + t <= n
    long long K2 = isqrtll(zeros);             // max t with t^2 <= total zeros
    long long K3 = ones;                       // max t with t <= total ones
    int K = (int)min({K1, K2, K3});

    unsigned long long ans = 0;
    const int* prefPtr = pref.data();
    for (int t = 1; t <= K; ++t) {
        ans += count_for_t(prefPtr, n, t);
    }

    cout << ans << "\n";
    return 0;
}