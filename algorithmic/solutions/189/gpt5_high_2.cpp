#include <bits/stdc++.h>
using namespace std;

static inline int code36(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    return 26 + (c - '0');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();
    const int n = (int)s1.size();
    const int m = (int)s2.size();

    auto naive_align = [&](string& T, int len1, int len2) {
        int c = min(len1, len2);
        if (c > 0) T.append(c, 'M');
        if (len1 > len2) T.append(len1 - len2, 'D');
        else if (len2 > len1) T.append(len2 - len1, 'I');
    };

    if (n == 0 && m == 0) {
        cout << "\n";
        return 0;
    }
    if (n == 0) {
        string T;
        T.reserve(m);
        T.append(m, 'I');
        cout << T << "\n";
        return 0;
    }
    if (m == 0) {
        string T;
        T.reserve(n);
        T.append(n, 'D');
        cout << T << "\n";
        return 0;
    }

    // Parameters
    const int K = 16; // k-mer length for anchors
    int step1 = 8;    // sampling step for S1
    if (n < 200000) step1 = 4;
    if (n < 50000) step1 = 2;
    if (n < 10000) step1 = 1;

    // If too short for anchors, just naive align whole strings
    if (n < K || m < K) {
        string T;
        T.reserve((size_t)n + m);
        naive_align(T, n, m);
        cout << T << "\n";
        return 0;
    }

    const uint64_t B = 1315423911ULL;
    uint64_t powBK = 1;
    for (int i = 0; i < K; ++i) powBK *= B;

    auto hash_k = [&](const string& s, int pos)->uint64_t {
        uint64_t h = 0;
        const unsigned char* p = (const unsigned char*)s.data() + pos;
        for (int i = 0; i < K; ++i) {
            h = h * B + (uint64_t)p[i];
        }
        return h;
    };

    // Build dictionary of S1 k-mers sampled every step1
    int count1 = (n - K) / step1 + 1;
    unordered_map<uint64_t, int> mp;
    mp.reserve((size_t)count1 * 2);
    mp.max_load_factor(0.7f);

    // Build small gating by first two chars
    vector<uint8_t> pairGate(36 * 36, 0);

    const char* s1d = s1.data();
    for (int p = 0; p <= n - K; p += step1) {
        uint64_t h = hash_k(s1, p);
        auto it = mp.find(h);
        if (it == mp.end()) {
            mp.emplace(h, p);
            int a = code36((unsigned char)s1d[p]);
            int b = code36((unsigned char)s1d[p + 1]);
            pairGate[a * 36 + b] = 1;
        } else {
            if (it->second >= 0) {
                // Confirm actual equality to disambiguate rare hash collisions; mark as duplicate otherwise
                bool same = (memcmp(s1d + it->second, s1d + p, K) == 0);
                if (!same) {
                    // Collision: mark as duplicate to be safe
                    it->second = -1;
                } else {
                    it->second = -1; // duplicate
                }
            }
        }
    }

    // Scan S2 with rolling hash step=1
    vector<pair<int,int>> anchors;
    anchors.reserve((size_t)min(n, m) / max(1, step1)); // heuristic reserve

    if (m >= K) {
        const char* s2d = s2.data();
        uint64_t h = 0;
        for (int i = 0; i < K; ++i) h = h * B + (uint64_t)(unsigned char)s2d[i];

        for (int q = 0; q <= m - K; ++q) {
            // Gate by first two chars to reduce lookups
            int a = code36((unsigned char)s2d[q]);
            int b = code36((unsigned char)s2d[q + 1]);
            if (pairGate[a * 36 + b]) {
                auto it = mp.find(h);
                if (it != mp.end() && it->second >= 0) {
                    int p = it->second;
                    if (memcmp(s1d + p, s2d + q, K) == 0) {
                        anchors.emplace_back(p, q);
                    }
                }
            }
            if (q + K < m) {
                h = h * B + (uint64_t)(unsigned char)s2d[q + K] - (uint64_t)(unsigned char)s2d[q] * powBK;
            }
        }
    }

    // If no anchors, fallback to naive alignment entire strings
    if (anchors.empty()) {
        string T;
        T.reserve((size_t)n + m);
        naive_align(T, n, m);
        cout << T << "\n";
        return 0;
    }

    // LIS on pos1 with anchors sorted by pos2 order (already increasing by q)
    int A = (int)anchors.size();
    vector<int> tailsVal;
    vector<int> tailsIdx;
    tailsVal.reserve(A);
    tailsIdx.reserve(A);
    vector<int> prev(A, -1);

    for (int i = 0; i < A; ++i) {
        int p = anchors[i].first;
        auto it = lower_bound(tailsVal.begin(), tailsVal.end(), p);
        int pos = (int)(it - tailsVal.begin());
        if (pos > 0) prev[i] = tailsIdx[pos - 1];
        if (pos == (int)tailsVal.size()) {
            tailsVal.push_back(p);
            tailsIdx.push_back(i);
        } else {
            tailsVal[pos] = p;
            tailsIdx[pos] = i;
        }
    }
    // Reconstruct LIS indices
    int idx = tailsIdx.back();
    vector<int> lisIdx;
    while (idx != -1) {
        lisIdx.push_back(idx);
        idx = prev[idx];
    }
    reverse(lisIdx.begin(), lisIdx.end());

    // Filter to ensure non-overlapping anchors (distance at least K in both strings)
    vector<pair<int,int>> chain;
    chain.reserve(lisIdx.size());
    int cur_i = 0, cur_j = 0;
    for (int id : lisIdx) {
        int p = anchors[id].first;
        int q = anchors[id].second;
        if (p >= cur_i && q >= cur_j) {
            chain.emplace_back(p, q);
            cur_i = p + K;
            cur_j = q + K;
        }
    }
    if (chain.empty()) {
        // Fallback naive again
        string T;
        T.reserve((size_t)n + m);
        naive_align(T, n, m);
        cout << T << "\n";
        return 0;
    }

    // Generate transcript
    string T;
    T.reserve((size_t)n + m);

    int i = 0, j = 0;
    for (auto [p, q] : chain) {
        int a = p - i;
        int b = q - j;
        if (a < 0) a = 0; // safety
        if (b < 0) b = 0;
        naive_align(T, a, b);
        T.append(K, 'M');
        i = p + K;
        j = q + K;
    }
    // Suffix
    if (i < n || j < m) {
        naive_align(T, n - i, m - j);
    }

    cout << T << "\n";
    return 0;
}