#include <bits/stdc++.h>
using namespace std;

struct FastWriter {
    static constexpr size_t BUF_SIZE = 1 << 20;
    string buf;
    FastWriter() { buf.reserve(BUF_SIZE * 2); }
    ~FastWriter() { flush(); }

    inline void flush() {
        if (!buf.empty()) {
            fwrite(buf.data(), 1, buf.size(), stdout);
            buf.clear();
        }
    }

    inline void write_repeat(char c, long long cnt) {
        while (cnt > 0) {
            size_t space = BUF_SIZE - buf.size();
            size_t chunk = (size_t)min<long long>(cnt, (long long)space);
            buf.append(chunk, c);
            cnt -= (long long)chunk;
            if (buf.size() >= BUF_SIZE) flush();
        }
    }

    inline void write_char(char c) {
        buf.push_back(c);
        if (buf.size() >= BUF_SIZE) flush();
    }
};

static inline uint64_t hash_kmer_fnv1a(const string& s, int pos, int k) {
    uint64_t h = 1469598103934665603ULL;
    for (int t = 0; t < k; ++t) {
        h ^= (uint8_t)s[pos + t];
        h *= 1099511628211ULL;
    }
    // extra mixing
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    return h;
}

static inline long long estimate_cost_for_delta(
    const string& s1, int o1, int n,
    const string& s2, int o2, int m,
    int delta
) {
    long long i = 0, j = 0;
    long long cost = 0;

    if (delta > 0) {
        long long ins = min<long long>(delta, m);
        cost += ins;
        j += ins;
    } else if (delta < 0) {
        long long del = min<long long>(-delta, n);
        cost += del;
        i += del;
    }

    long long overlap = min<long long>(n - i, m - j);
    long long remDel = (n - i) - overlap;
    long long remIns = (m - j) - overlap;

    long long samples = min<long long>(4096, overlap);
    if (samples > 0) {
        long long mism = 0;
        if (samples == 1) {
            if (s1[o1 + (int)i] != s2[o2 + (int)j]) mism = 1;
        } else {
            long long denom = samples - 1;
            long long maxpos = overlap - 1;
            for (long long t = 0; t < samples; ++t) {
                long long pos = (maxpos * t) / denom;
                if (s1[o1 + (int)(i + pos)] != s2[o2 + (int)(j + pos)]) ++mism;
            }
        }
        long long estSub = (mism * overlap) / samples;
        cost += estSub;
    }

    cost += remDel + remIns;
    return cost;
}

static int choose_delta(
    const string& s1, int o1, int n,
    const string& s2, int o2, int m
) {
    const int k = 32;
    const int step = 2048;

    vector<int> candidates;
    candidates.reserve(4);
    candidates.push_back(0);
    candidates.push_back(m - n);

    int bestDeltaVote = 0;
    int bestCnt = 0;

    if (n >= k && m >= k) {
        unordered_map<uint64_t, vector<int>> posMap;
        posMap.reserve((size_t)(m / step + 10));
        posMap.max_load_factor(0.7f);

        for (int p2 = 0; p2 + k <= m; p2 += step) {
            uint64_t h = hash_kmer_fnv1a(s2, o2 + p2, k);
            auto &vec = posMap[h];
            if ((int)vec.size() < 8) vec.push_back(p2);
        }

        unordered_map<int, int> cnt;
        cnt.reserve((size_t)(n / step + 10));
        cnt.max_load_factor(0.7f);

        for (int p1 = 0; p1 + k <= n; p1 += step) {
            uint64_t h = hash_kmer_fnv1a(s1, o1 + p1, k);
            auto it = posMap.find(h);
            if (it == posMap.end()) continue;
            for (int p2 : it->second) {
                if (memcmp(s1.data() + (o1 + p1), s2.data() + (o2 + p2), (size_t)k) != 0) continue;
                int d = p2 - p1;
                int c = ++cnt[d];
                if (c > bestCnt) {
                    bestCnt = c;
                    bestDeltaVote = d;
                }
            }
        }

        if (bestCnt > 0) candidates.push_back(bestDeltaVote);
    }

    sort(candidates.begin(), candidates.end());
    candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());

    int bestDelta = candidates[0];
    long long bestCost = LLONG_MAX;

    for (int d : candidates) {
        long long c = estimate_cost_for_delta(s1, o1, n, s2, o2, m, d);
        if (c < bestCost) {
            bestCost = c;
            bestDelta = d;
        }
    }
    return bestDelta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    int N = (int)s1.size();
    int M = (int)s2.size();

    int p = 0;
    int minNM = min(N, M);
    while (p < minNM && s1[p] == s2[p]) ++p;

    int s = 0;
    int maxs = min(N - p, M - p);
    while (s < maxs && s1[N - 1 - s] == s2[M - 1 - s]) ++s;

    int o1 = p, o2 = p;
    int n = N - p - s;
    int m = M - p - s;

    int delta = 0;
    if (n > 0 || m > 0) {
        delta = choose_delta(s1, o1, n, s2, o2, m);
    }

    FastWriter out;

    out.write_repeat('M', p);

    long long i = 0, j = 0;
    if (delta > 0) {
        long long ins = min<long long>(delta, m);
        out.write_repeat('I', ins);
        j += ins;
    } else if (delta < 0) {
        long long del = min<long long>(-delta, n);
        out.write_repeat('D', del);
        i += del;
    }

    long long overlap = min<long long>(n - i, m - j);
    out.write_repeat('M', overlap);
    i += overlap;
    j += overlap;

    if (i < n) out.write_repeat('D', n - i);
    if (j < m) out.write_repeat('I', m - j);

    out.write_repeat('M', s);

    out.write_char('\n');
    out.flush();
    return 0;
}