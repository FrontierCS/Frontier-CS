#include <bits/stdc++.h>
using namespace std;

static inline uint8_t codeChar(unsigned char c) {
    if (c >= 'A' && c <= 'Z') return uint8_t(c - 'A');
    return uint8_t(26 + (c - '0'));
}

struct PairIJ {
    int i;
    int j;
};

template <typename F>
static inline void for_each_minimizer(const string &s, int k, int w, F cb) {
    const int L = (int)s.size();
    if (L < k) return;
    int Lk = L - k + 1;
    if (Lk <= 0) return;
    int W = w;
    if (W <= 0) W = 1;
    if (W > Lk) W = Lk;

    const uint64_t base = 11400714819323198485ull; // odd 64-bit
    uint64_t powk = 1;
    for (int i = 0; i < k; ++i) powk *= base;

    // compute initial hash for position 0
    uint64_t h = 0;
    for (int t = 0; t < k; ++t) {
        uint64_t v = (uint64_t)codeChar((unsigned char)s[t]) + 1ull;
        h = h * base + v;
    }

    deque<pair<int, uint64_t>> dq; // (pos, hash)
    auto push_hash = [&](int p, uint64_t hv) {
        while (!dq.empty() && dq.back().second > hv) dq.pop_back();
        dq.emplace_back(p, hv);
    };
    auto pop_expired = [&](int p) {
        int left = p - W + 1;
        while (!dq.empty() && dq.front().first < left) dq.pop_front();
    };

    int last_pos = -1;

    // process position 0
    push_hash(0, h);
    if (0 >= W - 1) {
        pop_expired(0);
        int cur_pos = dq.front().first;
        if (cur_pos != last_pos) {
            cb(cur_pos, dq.front().second);
            last_pos = cur_pos;
        }
    }

    for (int p = 1; p < Lk; ++p) {
        uint64_t v_out = (uint64_t)codeChar((unsigned char)s[p - 1]) + 1ull;
        uint64_t v_in  = (uint64_t)codeChar((unsigned char)s[p + k - 1]) + 1ull;
        h = h * base + v_in - powk * v_out;
        push_hash(p, h);
        if (p >= W - 1) {
            pop_expired(p);
            int cur_pos = dq.front().first;
            if (cur_pos != last_pos) {
                cb(cur_pos, dq.front().second);
                last_pos = cur_pos;
            }
        }
    }
}

static inline int chooseNearest(const vector<int>& v, int target) {
    if (v.empty()) return -1;
    auto it = lower_bound(v.begin(), v.end(), target);
    if (it == v.end()) return v.back();
    if (it == v.begin()) return *it;
    int a = *it;
    int b = *(it - 1);
    return (abs(a - target) <= abs(b - target)) ? a : b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    int n = (int)s1.size();
    int m = (int)s2.size();

    // Heuristic parameter selection based on length
    int k, w;
    int Lmax = max(n, m);
    if (Lmax < 100000) { k = 10; w = 30; }
    else if (Lmax < 1000000) { k = 13; w = 50; }
    else if (Lmax < 5000000) { k = 15; w = 80; }
    else { k = 17; w = 100; }

    // If strings too short for minimizers, do naive alignment
    if (n < k || m < k) {
        string out;
        out.reserve((size_t)max(n, m));
        int common = min(n, m);
        if (common > 0) out.append((size_t)common, 'M');
        if (n > common) out.append((size_t)(n - common), 'D');
        if (m > common) out.append((size_t)(m - common), 'I');
        cout << out;
        return 0;
    }

    // Build minimizer map for s2: hash -> sorted positions
    unordered_map<uint64_t, vector<int>> mp;
    size_t approxAnch2 = 2ull * (size_t)(m - k + 1) / (size_t)(w + 1) + 16;
    mp.reserve(approxAnch2 * 2);

    for_each_minimizer(s2, k, w, [&](int pos, uint64_t h) {
        mp[h].push_back(pos);
    });

    // Produce candidate pairs (one per s1 minimizer) using nearest to diagonal
    vector<PairIJ> pairs;
    pairs.reserve(2ull * (size_t)(n - k + 1) / (size_t)(w + 1) + 16);
    double ratio = (n > 0) ? (double)m / (double)n : 1.0;

    for_each_minimizer(s1, k, w, [&](int pos1, uint64_t h) {
        auto it = mp.find(h);
        if (it == mp.end()) return;
        const vector<int>& v = it->second;
        if (v.empty()) return;
        int j0 = (int)llround((double)pos1 * ratio);
        if (j0 < 0) j0 = 0;
        if (j0 > m - k) j0 = max(0, m - k);
        int pos2 = chooseNearest(v, j0);
        if (pos2 >= 0) {
            pairs.push_back({pos1, pos2});
        }
    });

    // If no anchors, fallback naive alignment
    if (pairs.empty()) {
        string out;
        out.reserve((size_t)max(n, m));
        int common = min(n, m);
        if (common > 0) out.append((size_t)common, 'M');
        if (n > common) out.append((size_t)(n - common), 'D');
        if (m > common) out.append((size_t)(m - common), 'I');
        cout << out;
        return 0;
    }

    // LIS on j to get increasing chain (i is already increasing by construction)
    vector<int> tails_j;
    vector<int> tails_idx;
    tails_j.reserve(pairs.size());
    tails_idx.reserve(pairs.size());
    vector<int> prev_idx(pairs.size(), -1);

    for (size_t t = 0; t < pairs.size(); ++t) {
        int j = pairs[t].j;
        auto it = lower_bound(tails_j.begin(), tails_j.end(), j);
        int pos = (int)(it - tails_j.begin());
        if (pos == (int)tails_j.size()) {
            tails_j.push_back(j);
            tails_idx.push_back((int)t);
        } else {
            tails_j[pos] = j;
            tails_idx[pos] = (int)t;
        }
        prev_idx[t] = (pos > 0 ? tails_idx[pos - 1] : -1);
    }

    // Reconstruct LIS
    vector<int> chain_indices;
    if (!tails_idx.empty()) {
        int idx = tails_idx.back();
        while (idx >= 0) {
            chain_indices.push_back(idx);
            idx = prev_idx[idx];
        }
        reverse(chain_indices.begin(), chain_indices.end());
    }

    // Build transcript using anchors in chain
    string out;
    out.reserve((size_t)max(n, m) + 32);

    auto append_repeat = [&](char c, int cnt) {
        if (cnt > 0) out.append((size_t)cnt, c);
    };

    int i0 = 0, j0 = 0;

    auto align_to = [&](int ai, int aj) {
        int di = ai - i0;
        int dj = aj - j0;
        if (di < 0) di = 0; // should not happen
        if (dj < 0) dj = 0; // should not happen
        int mm = min(di, dj);
        append_repeat('M', mm);
        i0 += mm;
        j0 += mm;
        if (di > mm) {
            append_repeat('D', di - mm);
            i0 += di - mm;
        }
        if (dj > mm) {
            append_repeat('I', dj - mm);
            j0 += dj - mm;
        }
    };

    for (int idx : chain_indices) {
        int ai = pairs[idx].i;
        int aj = pairs[idx].j;
        if (ai < i0) ai = i0;
        if (aj < j0) aj = j0;
        align_to(ai, aj);
        int len = k;
        if (i0 + len > n) len = n - i0;
        if (j0 + len > m) len = m - j0;
        if (len > 0) {
            append_repeat('M', len);
            i0 += len;
            j0 += len;
        }
        if (i0 >= n || j0 >= m) break;
    }

    // Align rest
    align_to(n, m);

    cout << out;
    return 0;
}