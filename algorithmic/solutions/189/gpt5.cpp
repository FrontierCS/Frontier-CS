#include <bits/stdc++.h>
using namespace std;

static inline void write_repeat(FILE* f, char ch, size_t cnt) {
    static const size_t BUFSZ = 1 << 20; // 1 MiB
    static vector<char> buf(BUFSZ);
    // Fill buffer with ch
    memset(buf.data(), ch, BUFSZ);
    while (cnt >= BUFSZ) {
        fwrite(buf.data(), 1, BUFSZ, f);
        cnt -= BUFSZ;
    }
    if (cnt > 0) {
        fwrite(buf.data(), 1, cnt, f);
    }
}

static inline uint64_t hash_block(const char* p, size_t k) {
    // FNV-1a 64-bit
    uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < k; ++i) {
        h ^= (unsigned char)p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) s1.clear();
    if (!getline(cin, s2)) s2.clear();
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const size_t n = s1.size();
    const size_t m = s2.size();

    // Compute LCP
    size_t lcp = 0;
    {
        size_t lim = min(n, m);
        const char* a = s1.data();
        const char* b = s2.data();
        while (lcp < lim && a[lcp] == b[lcp]) ++lcp;
    }

    // Compute LCSuffix without overlapping LCP
    size_t lcsuf = 0;
    {
        size_t lim = min(n, m) - lcp;
        const char* a = s1.data();
        const char* b = s2.data();
        while (lcsuf < lim && a[n - 1 - lcsuf] == b[m - 1 - lcsuf]) ++lcsuf;
    }

    size_t n_mid = n - lcp - lcsuf;
    size_t m_mid = m - lcp - lcsuf;

    // Determine a good delta using sampled k-gram anchors (approximate)
    int bestDelta = 0;
    int bestCount = 0;

    const size_t K = 16;          // k-gram length
    const size_t STEP = 64;       // sampling step

    if (n_mid >= K && m_mid >= K) {
        // Build hash map for S2 middle region
        unordered_map<uint64_t, uint32_t> posMap;
        size_t samples2 = 1 + (m_mid - K) / STEP;
        posMap.reserve(samples2 * 2 + 16);

        const char* p2 = s2.data() + lcp;
        for (size_t pos2 = 0; pos2 + K <= m_mid; pos2 += STEP) {
            uint64_t h = hash_block(p2 + pos2, K);
            // store first occurrence only
            if (posMap.find(h) == posMap.end()) posMap.emplace(h, (uint32_t)pos2);
        }

        unordered_map<int, int> deltaCount;
        size_t samples1 = 1 + (n_mid - K) / STEP;
        deltaCount.reserve(samples1 * 2 + 16);

        const char* p1 = s1.data() + lcp;
        for (size_t pos1 = 0; pos1 + K <= n_mid; pos1 += STEP) {
            uint64_t h = hash_block(p1 + pos1, K);
            auto it = posMap.find(h);
            if (it != posMap.end()) {
                int d = (int)it->second - (int)pos1;
                int c = ++deltaCount[d];
                if (c > bestCount) {
                    bestCount = c;
                    bestDelta = d;
                }
            }
        }
        // Clamp delta to feasible range
        if (bestDelta > (int)m_mid) bestDelta = (int)m_mid;
        if (bestDelta < -(int)n_mid) bestDelta = -(int)n_mid;
    }

    FILE* out = stdout;

    // Output transcript:
    // 1) LCP matches
    write_repeat(out, 'M', lcp);

    // 2) Middle region with initial offset bestDelta
    size_t startI = 0, startD = 0;
    if (bestDelta > 0) {
        // insert delta chars from S2
        startI = (size_t)bestDelta;
        if (startI > m_mid) startI = m_mid;
        write_repeat(out, 'I', startI);
    } else if (bestDelta < 0) {
        // delete -delta chars from S1
        startD = (size_t)(-bestDelta);
        if (startD > n_mid) startD = n_mid;
        write_repeat(out, 'D', startD);
    }

    size_t n_rem = n_mid - startD;
    size_t m_rem = m_mid - startI;
    size_t midM = min(n_rem, m_rem);
    write_repeat(out, 'M', midM);

    // Remaining in middle
    if (n_rem > m_rem) {
        write_repeat(out, 'D', n_rem - m_rem);
    } else if (m_rem > n_rem) {
        write_repeat(out, 'I', m_rem - n_rem);
    }

    // 3) LCSuffix matches
    write_repeat(out, 'M', lcsuf);

    fputc('\n', out);
    fflush(out);
    return 0;
}