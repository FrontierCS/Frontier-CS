#include <bits/stdc++.h>

#if defined(__x86_64__) || defined(__i386__)
#include <immintrin.h>
#endif

using namespace std;

static inline uint64_t countMatches(const uint32_t* a, const uint32_t* b, size_t len, uint32_t k) {
    uint64_t cnt = 0;

#if defined(__AVX2__)
    size_t i = 0;
    const __m256i vk = _mm256_set1_epi32((int)k);

    __m256i acc0 = _mm256_setzero_si256();
    __m256i acc1 = _mm256_setzero_si256();

    for (; i + 16 <= len; i += 16) {
        const __m256i va0 = _mm256_loadu_si256((const __m256i*)(a + i));
        const __m256i vb0 = _mm256_loadu_si256((const __m256i*)(b + i));
        const __m256i va1 = _mm256_loadu_si256((const __m256i*)(a + i + 8));
        const __m256i vb1 = _mm256_loadu_si256((const __m256i*)(b + i + 8));

        const __m256i cmp0 = _mm256_cmpeq_epi32(_mm256_add_epi32(va0, vk), vb0);
        const __m256i cmp1 = _mm256_cmpeq_epi32(_mm256_add_epi32(va1, vk), vb1);

        acc0 = _mm256_add_epi32(acc0, _mm256_srli_epi32(cmp0, 31));
        acc1 = _mm256_add_epi32(acc1, _mm256_srli_epi32(cmp1, 31));
    }

    __m256i acc = _mm256_add_epi32(acc0, acc1);
    alignas(32) uint32_t tmp8[8];
    _mm256_store_si256((__m256i*)tmp8, acc);
    cnt += (uint64_t)tmp8[0] + tmp8[1] + tmp8[2] + tmp8[3] + tmp8[4] + tmp8[5] + tmp8[6] + tmp8[7];

    __m256i acc2 = _mm256_setzero_si256();
    for (; i + 8 <= len; i += 8) {
        const __m256i va = _mm256_loadu_si256((const __m256i*)(a + i));
        const __m256i vb = _mm256_loadu_si256((const __m256i*)(b + i));
        const __m256i cmp = _mm256_cmpeq_epi32(_mm256_add_epi32(va, vk), vb);
        acc2 = _mm256_add_epi32(acc2, _mm256_srli_epi32(cmp, 31));
    }
    _mm256_store_si256((__m256i*)tmp8, acc2);
    cnt += (uint64_t)tmp8[0] + tmp8[1] + tmp8[2] + tmp8[3] + tmp8[4] + tmp8[5] + tmp8[6] + tmp8[7];

    for (; i < len; ++i) cnt += (b[i] == a[i] + k);

#elif defined(__SSE2__)
    size_t i = 0;
    const __m128i vk = _mm_set1_epi32((int)k);

    __m128i acc0 = _mm_setzero_si128();
    __m128i acc1 = _mm_setzero_si128();

    for (; i + 8 <= len; i += 8) {
        const __m128i va0 = _mm_loadu_si128((const __m128i*)(a + i));
        const __m128i vb0 = _mm_loadu_si128((const __m128i*)(b + i));
        const __m128i va1 = _mm_loadu_si128((const __m128i*)(a + i + 4));
        const __m128i vb1 = _mm_loadu_si128((const __m128i*)(b + i + 4));

        const __m128i cmp0 = _mm_cmpeq_epi32(_mm_add_epi32(va0, vk), vb0);
        const __m128i cmp1 = _mm_cmpeq_epi32(_mm_add_epi32(va1, vk), vb1);

        acc0 = _mm_add_epi32(acc0, _mm_srli_epi32(cmp0, 31));
        acc1 = _mm_add_epi32(acc1, _mm_srli_epi32(cmp1, 31));
    }

    __m128i acc = _mm_add_epi32(acc0, acc1);
    alignas(16) uint32_t tmp4[4];
    _mm_store_si128((__m128i*)tmp4, acc);
    cnt += (uint64_t)tmp4[0] + tmp4[1] + tmp4[2] + tmp4[3];

    __m128i acc2 = _mm_setzero_si128();
    for (; i + 4 <= len; i += 4) {
        const __m128i va = _mm_loadu_si128((const __m128i*)(a + i));
        const __m128i vb = _mm_loadu_si128((const __m128i*)(b + i));
        const __m128i cmp = _mm_cmpeq_epi32(_mm_add_epi32(va, vk), vb);
        acc2 = _mm_add_epi32(acc2, _mm_srli_epi32(cmp, 31));
    }
    _mm_store_si128((__m128i*)tmp4, acc2);
    cnt += (uint64_t)tmp4[0] + tmp4[1] + tmp4[2] + tmp4[3];

    for (; i < len; ++i) cnt += (b[i] == a[i] + k);

#else
    for (size_t i = 0; i < len; ++i) cnt += (b[i] == a[i] + k);
#endif

    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    const int n = (int)s.size();

    vector<uint32_t> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) pref[i + 1] = pref[i] + (s[i] == '1');

    const uint32_t onesTotal = pref[n];
    const uint32_t zerosTotal = (uint32_t)n - onesTotal;

    int kmaxLen = 0;
    for (int k = 1;; ++k) {
        long long L = 1LL * k * (k + 1);
        if (L > n) break;
        kmaxLen = k;
    }

    int kmax = kmaxLen;
    kmax = min(kmax, (int)onesTotal);
    kmax = min(kmax, (int)floor(sqrt((long double)zerosTotal)));

    if (kmax <= 0) {
        cout << 0 << '\n';
        return 0;
    }

    uint64_t ans = 0;
    const uint32_t* p = pref.data();
    for (int k = 1; k <= kmax; ++k) {
        const int L = k * (k + 1);
        const size_t len = (size_t)(n - L + 1);
        ans += countMatches(p, p + L, len, (uint32_t)k);
    }

    cout << ans << '\n';
    return 0;
}