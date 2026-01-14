#include <bits/stdc++.h>
#include <immintrin.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    const int n = (int)s.size();

    vector<int> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) pref[i + 1] = pref[i] + (s[i] == '1');

    const int totalOnes = pref[n];
    const int totalZeros = n - totalOnes;

    long double disc = sqrtl(1.0L + 4.0L * (long double)n);
    int kLenMax = (int)((disc - 1.0L) / 2.0L);
    int kZeroMax = (int)floorl(sqrtl((long double)totalZeros));
    int kMax = min({kLenMax, totalOnes, kZeroMax});

    long long ans = 0;

#if defined(__SSE2__)
    static const int pop4[16] = {0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4};
    const int* base = pref.data();

    for (int k = 1; k <= kMax; ++k) {
        int d = k * (k + 1);
        if (d > n) break;

        const int* a = base;
        const int* b = base + d;
        int len = n - d + 1;

        long long cnt = 0;
        __m128i vk = _mm_set1_epi32(k);

        int i = 0;
        for (; i + 8 <= len; i += 8) {
            __m128i va0 = _mm_loadu_si128((const __m128i*)(a + i));
            __m128i vb0 = _mm_loadu_si128((const __m128i*)(b + i));
            __m128i cmp0 = _mm_cmpeq_epi32(_mm_add_epi32(va0, vk), vb0);
            int mask0 = _mm_movemask_ps(_mm_castsi128_ps(cmp0));
            cnt += pop4[mask0];

            __m128i va1 = _mm_loadu_si128((const __m128i*)(a + i + 4));
            __m128i vb1 = _mm_loadu_si128((const __m128i*)(b + i + 4));
            __m128i cmp1 = _mm_cmpeq_epi32(_mm_add_epi32(va1, vk), vb1);
            int mask1 = _mm_movemask_ps(_mm_castsi128_ps(cmp1));
            cnt += pop4[mask1];
        }
        for (; i + 4 <= len; i += 4) {
            __m128i va = _mm_loadu_si128((const __m128i*)(a + i));
            __m128i vb = _mm_loadu_si128((const __m128i*)(b + i));
            __m128i cmp = _mm_cmpeq_epi32(_mm_add_epi32(va, vk), vb);
            int mask = _mm_movemask_ps(_mm_castsi128_ps(cmp));
            cnt += pop4[mask];
        }
        for (; i < len; ++i) cnt += (b[i] == a[i] + k);

        ans += cnt;
    }
#else
    const int* base = pref.data();
    for (int k = 1; k <= kMax; ++k) {
        int d = k * (k + 1);
        if (d > n) break;
        const int* a = base;
        const int* b = base + d;
        int len = n - d + 1;

        long long cnt = 0;
        for (int i = 0; i < len; ++i) cnt += (b[i] == a[i] + k);
        ans += cnt;
    }
#endif

    cout << ans << '\n';
    return 0;
}