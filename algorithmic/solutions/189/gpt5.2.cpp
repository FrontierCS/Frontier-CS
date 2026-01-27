#include <bits/stdc++.h>
using namespace std;

struct FastHash {
    size_t operator()(uint64_t x) const noexcept {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return (size_t)(x ^ (x >> 31));
    }
};

static inline void trim_cr(string &s) {
    if (!s.empty() && s.back() == '\r') s.pop_back();
}

static inline int lcp_limit(const char* a, int ai, int aEnd, const char* b, int bi, int bEnd, int limit) {
    int l = 0;
    int maxA = aEnd - ai;
    int maxB = bEnd - bi;
    int maxL = min(limit, min(maxA, maxB));
    while (l < maxL && a[ai + l] == b[bi + l]) ++l;
    return l;
}

static vector<pair<int,int>> lis_anchors(const vector<pair<int,int>> &cand) {
    int A = (int)cand.size();
    if (A == 0) return {};

    vector<int> tailPos;
    vector<int> tailIdx;
    tailPos.reserve(A);
    tailIdx.reserve(A);
    vector<int> prev(A, -1);

    for (int idx = 0; idx < A; ++idx) {
        int pos2 = cand[idx].second;
        auto it = lower_bound(tailPos.begin(), tailPos.end(), pos2);
        int k = (int)(it - tailPos.begin());
        if (it == tailPos.end()) {
            tailPos.push_back(pos2);
            tailIdx.push_back(idx);
        } else {
            *it = pos2;
            tailIdx[k] = idx;
        }
        prev[idx] = (k > 0) ? tailIdx[k - 1] : -1;
    }

    vector<pair<int,int>> seq;
    int idx = tailIdx.empty() ? -1 : tailIdx.back();
    while (idx != -1) {
        seq.push_back(cand[idx]);
        idx = prev[idx];
    }
    reverse(seq.begin(), seq.end());
    return seq;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;
    trim_cr(s1);
    trim_cr(s2);

    const int N = (int)s1.size();
    const int M = (int)s2.size();

    int idxmap[256];
    uint64_t valmap[256];
    for (int i = 0; i < 256; ++i) idxmap[i] = -1, valmap[i] = 0;

    for (int d = 0; d <= 9; ++d) {
        idxmap[(unsigned char)('0' + d)] = d;
        valmap[(unsigned char)('0' + d)] = (uint64_t)(d + 1);
    }
    for (int a = 0; a < 26; ++a) {
        idxmap[(unsigned char)('A' + a)] = 10 + a;
        valmap[(unsigned char)('A' + a)] = (uint64_t)(11 + a);
    }

    array<vector<int>, 36> pos1, pos2;
    {
        array<int,36> cnt{};
        for (int i = 0; i < N; ++i) ++cnt[idxmap[(unsigned char)s1[i]]];
        for (int c = 0; c < 36; ++c) pos1[c].reserve(cnt[c]);
        for (int i = 0; i < N; ++i) pos1[idxmap[(unsigned char)s1[i]]].push_back(i);
    }
    {
        array<int,36> cnt{};
        for (int i = 0; i < M; ++i) ++cnt[idxmap[(unsigned char)s2[i]]];
        for (int c = 0; c < 36; ++c) pos2[c].reserve(cnt[c]);
        for (int i = 0; i < M; ++i) pos2[idxmap[(unsigned char)s2[i]]].push_back(i);
    }

    const char* a = s1.data();
    const char* b = s2.data();

    // Anchor hashing parameters
    const int K = 24;
    const int STRIDE = 32;

    uint64_t base = 0x9e3779b185ebca87ULL;
    base |= 1ULL;

    auto compute_powk = [&](int k) -> uint64_t {
        uint64_t p = 1;
        for (int i = 0; i < k; ++i) p *= base;
        return p;
    };

    auto scan_hashes = [&](const string& s, int k, int stride, auto &&fn) {
        int L = (int)s.size();
        if (L < k) return;
        uint64_t powK = compute_powk(k);
        uint64_t h = 0;
        for (int i = 0; i < k; ++i) h = h * base + valmap[(unsigned char)s[i]];
        int last = L - k;
        int nextSample = 0;
        for (int pos = 0; pos <= last; ++pos) {
            if (pos == nextSample) {
                fn(pos, h);
                nextSample += stride;
            }
            if (pos < last) {
                h = h * base + valmap[(unsigned char)s[pos + k]] - valmap[(unsigned char)s[pos]] * powK;
            }
        }
    };

    vector<pair<int,int>> anchors;
    {
        int samples2 = (M >= K) ? ((M - K) / STRIDE + 1) : 0;
        unordered_map<uint64_t, int, FastHash> mp;
        mp.reserve((size_t)samples2 * 2 + 1);
        mp.max_load_factor(0.7f);

        scan_hashes(s2, K, STRIDE, [&](int pos, uint64_t h) {
            auto it = mp.find(h);
            if (it == mp.end()) mp.emplace(h, pos);
            else it->second = -1;
        });

        int samples1 = (N >= K) ? ((N - K) / STRIDE + 1) : 0;
        vector<pair<int,int>> cand;
        cand.reserve(min(samples1, samples2));

        scan_hashes(s1, K, STRIDE, [&](int pos, uint64_t h) {
            auto it = mp.find(h);
            if (it != mp.end() && it->second >= 0) cand.emplace_back(pos, it->second);
        });

        auto seq = lis_anchors(cand);

        // Filter overlapping anchors
        anchors.reserve(seq.size());
        int last1 = -K, last2 = -K;
        for (auto [p1, p2] : seq) {
            if (p1 + K > N || p2 + K > M) continue;
            if (p1 >= last1 + K && p2 >= last2 + K) {
                anchors.emplace_back(p1, p2);
                last1 = p1;
                last2 = p2;
            }
        }
    }

    array<int,36> ptr1{}, ptr2{};

    auto nextPos1 = [&](int cidx, int cur) -> int {
        auto &v = pos1[cidx];
        int &p = ptr1[cidx];
        int sz = (int)v.size();
        while (p < sz && v[p] < cur) ++p;
        return (p < sz) ? v[p] : INT_MAX;
    };
    auto nextPos2 = [&](int cidx, int cur) -> int {
        auto &v = pos2[cidx];
        int &p = ptr2[cidx];
        int sz = (int)v.size();
        while (p < sz && v[p] < cur) ++p;
        return (p < sz) ? v[p] : INT_MAX;
    };

    string out;
    out.reserve((size_t)N + (size_t)M + 1024);

    const int W = 64;
    const int LCP_STRONG = 32;
    const int LCP_STRONG_LIMIT = 64;
    const int LCP_TIE_LIMIT = 16;

    auto align_segment = [&](int &i, int &j, int iEnd, int jEnd) {
        while (i < iEnd && j < jEnd) {
            int ii = i, jj = j;
            while (ii < iEnd && jj < jEnd && a[ii] == b[jj]) { ++ii; ++jj; }
            if (ii != i) {
                out.append((size_t)(ii - i), 'M');
                i = ii; j = jj;
                continue;
            }

            unsigned char c2 = (unsigned char)b[j];
            unsigned char c1 = (unsigned char)a[i];
            int idx2 = idxmap[c2];
            int idx1 = idxmap[c1];

            int p = nextPos1(idx2, i);
            int q = nextPos2(idx1, j);
            if (p >= iEnd) p = INT_MAX;
            if (q >= jEnd) q = INT_MAX;

            int del = (p == INT_MAX) ? INT_MAX : (p - i);
            int ins = (q == INT_MAX) ? INT_MAX : (q - j);

            bool delAllowed = (del != INT_MAX && del <= W);
            bool insAllowed = (ins != INT_MAX && ins <= W);

            bool delStrong = false, insStrong = false;
            int lcpDel = 0, lcpIns = 0;

            if (del != INT_MAX && del > W) {
                lcpDel = lcp_limit(a, p, iEnd, b, j, jEnd, LCP_STRONG_LIMIT);
                delStrong = (lcpDel >= LCP_STRONG);
                delAllowed = delAllowed || delStrong;
            }
            if (ins != INT_MAX && ins > W) {
                lcpIns = lcp_limit(a, i, iEnd, b, q, jEnd, LCP_STRONG_LIMIT);
                insStrong = (lcpIns >= LCP_STRONG);
                insAllowed = insAllowed || insStrong;
            }

            if (delStrong != insStrong) {
                if (delStrong) {
                    out.append((size_t)del, 'D');
                    i = p;
                } else {
                    out.append((size_t)ins, 'I');
                    j = q;
                }
                continue;
            }

            if (delAllowed && insAllowed) {
                if (del < ins) {
                    out.append((size_t)del, 'D');
                    i = p;
                } else if (ins < del) {
                    out.append((size_t)ins, 'I');
                    j = q;
                } else {
                    // Tie: lookahead a bit
                    int tDel = (p != INT_MAX) ? lcp_limit(a, p, iEnd, b, j, jEnd, LCP_TIE_LIMIT) : -1;
                    int tIns = (q != INT_MAX) ? lcp_limit(a, i, iEnd, b, q, jEnd, LCP_TIE_LIMIT) : -1;
                    if (tIns > tDel) {
                        out.append((size_t)ins, 'I');
                        j = q;
                    } else {
                        out.append((size_t)del, 'D');
                        i = p;
                    }
                }
                continue;
            }

            if (delAllowed) {
                out.append((size_t)del, 'D');
                i = p;
                continue;
            }
            if (insAllowed) {
                out.append((size_t)ins, 'I');
                j = q;
                continue;
            }

            out.push_back('M');
            ++i; ++j;
        }

        if (i < iEnd) {
            out.append((size_t)(iEnd - i), 'D');
            i = iEnd;
        }
        if (j < jEnd) {
            out.append((size_t)(jEnd - j), 'I');
            j = jEnd;
        }
    };

    int i = 0, j = 0;
    for (auto [ai, bj] : anchors) {
        if (ai < i || bj < j) continue;
        if (ai > N || bj > M) continue;
        align_segment(i, j, ai, bj);
        if (ai + K <= N && bj + K <= M) {
            out.append((size_t)K, 'M');
            i = ai + K;
            j = bj + K;
        } else {
            break;
        }
    }
    align_segment(i, j, N, M);

    cout.write(out.data(), (streamsize)out.size());
    cout.put('\n');
    return 0;
}