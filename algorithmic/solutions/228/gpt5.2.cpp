#include <bits/stdc++.h>
#if defined(__AVX2__)
#include <immintrin.h>
#endif

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    const size_t n = s.size();

    vector<int32_t> pref(n + 1);
    for (size_t i = 0; i < n; ++i) pref[i + 1] = pref[i] + (s[i] == '1');

    unsigned long long ans = 0;

    for (int k = 1;; ++k) {
        const size_t L = (size_t)k * (size_t)(k + 1);
        if (L > n) break;

        const size_t m = n - L + 1;
        const int32_t* a = pref.data();
        const int32_t* b = pref.data() + L;

#if defined(__AVX2__)
        const __m256i vk = _mm256_set1_epi32(k);
        __m256i c0 = _mm256_setzero_si256();
        __m256i c1 = _mm256_setzero_si256();
        __m256i c2 = _mm256_setzero_si256();
        __m256i c3 = _mm256_setzero_si256();

        size_t i = 0;
        for (; i + 32 <= m; i += 32) {
            __m256i va0 = _mm256_loadu_si256((const __m256i*)(a + i));
            __m256i vb0 = _mm256_loadu_si256((const __m256i*)(b + i));
            __m256i ve0 = _mm256_cmpeq_epi32(_mm256_sub_epi32(vb0, va0), vk);
            c0 = _mm256_add_epi32(c0, _mm256_srli_epi32(ve0, 31));

            __m256i va1 = _mm256_loadu_si256((const __m256i*)(a + i + 8));
            __m256i vb1 = _mm256_loadu_si256((const __m256i*)(b + i + 8));
            __m256i ve1 = _mm256_cmpeq_epi32(_mm256_sub_epi32(vb1, va1), vk);
            c1 = _mm256_add_epi32(c1, _mm256_srli_epi32(ve1, 31));

            __m256i va2 = _mm256_loadu_si256((const __m256i*)(a + i + 16));
            __m256i vb2 = _mm256_loadu_si256((const __m256i*)(b + i + 16));
            __m256i ve2 = _mm256_cmpeq_epi32(_mm256_sub_epi32(vb2, va2), vk);
            c2 = _mm256_add_epi32(c2, _mm256_srli_epi32(ve2, 31));

            __m256i va3 = _mm256_loadu_si256((const __m256i*)(a + i + 24));
            __m256i vb3 = _mm256_loadu_si256((const __m256i*)(b + i + 24));
            __m256i ve3 = _mm256_cmpeq_epi32(_mm256_sub_epi32(vb3, va3), vk);
            c3 = _mm256_add_epi32(c3, _mm256_srli_epi32(ve3, 31));
        }

        __m256i vcnt = _mm256_add_epi32(_mm256_add_epi32(c0, c1), _mm256_add_epi32(c2, c3));
        for (; i + 8 <= m; i += 8) {
            __m256i va = _mm256_loadu_si256((const __m256i*)(a + i));
            __m256i vb = _mm256_loadu_si256((const __m256i*)(b + i));
            __m256i veq = _mm256_cmpeq_epi32(_mm256_sub_epi32(vb, va), vk);
            vcnt = _mm256_add_epi32(vcnt, _mm256_srli_epi32(veq, 31));
        }

        alignas(32) uint32_t tmp[8];
        _mm256_store_si256((__m256i*)tmp, vcnt);
        ans += (unsigned long long)tmp[0] + tmp[1] + tmp[2] + tmp[3] + tmp[4] + tmp[5] + tmp[6] + tmp[7];

        for (; i < m; ++i) ans += (unsigned long long)((b[i] - a[i]) == k);

#else
        size_t i = 0;
        for (; i + 8 <= m; i += 8) {
            ans += (unsigned long long)((b[i] - a[i]) == k);
            ans += (unsigned long long)((b[i + 1] - a[i + 1]) == k);
            ans += (unsigned long long)((b[i + 2] - a[i + 2]) == k);
            ans += (unsigned long long)((b[i + 3] - a[i + 3]) == k);
            ans += (unsigned long long)((b[i + 4] - a[i + 4]) == k);
            ans += (unsigned long long)((b[i + 5] - a[i + 5]) == k);
            ans += (unsigned long long)((b[i + 6] - a[i + 6]) == k);
            ans += (unsigned long long)((b[i + 7] - a[i + 7]) == k);
        }
        for (; i < m; ++i) ans += (unsigned long long)((b[i] - a[i]) == k);
#endif
    }

    cout << ans << '\n';
    return 0;
}