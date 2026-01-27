#include <bits/stdc++.h>
using namespace std;

static inline uint64_t fnv1a_hash(const char* s, int pos, int k) {
    uint64_t h = 1469598103934665603ULL;
    const unsigned char* p = reinterpret_cast<const unsigned char*>(s + pos);
    for (int i = 0; i < k; ++i) {
        h ^= (uint64_t)p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

static inline void align_gap(string &res, int &i, int &j, int si, int sj) {
    // Align from (i, j) to (si, sj) using simple operations
    int di = si - i;
    int dj = sj - j;
    if (di > dj) {
        res.append((size_t)(di - dj), 'D');
        i += (di - dj);
    } else if (dj > di) {
        res.append((size_t)(dj - di), 'I');
        j += (dj - di);
    }
    int k = min(di, dj);
    if (k > 0) {
        res.append((size_t)k, 'M');
        i += k;
        j += k;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string S1, S2;
    if (!getline(cin, S1)) return 0;
    if (!getline(cin, S2)) S2.clear();

    int n = (int)S1.size();
    int m = (int)S2.size();
    const char* a = S1.c_str();
    const char* b = S2.c_str();

    string res;
    res.reserve((size_t)n + (size_t)m); // upper bound (safe)

    // Common prefix
    int pre = 0;
    while (pre < n && pre < m && a[pre] == b[pre]) pre++;
    res.append((size_t)pre, 'M');

    // Common suffix (avoid overlap with prefix)
    int i = pre, j = pre;
    int ri = n - 1, rj = m - 1;
    int suf = 0;
    while (ri >= i && rj >= j && a[ri] == b[rj]) {
        ri--; rj--; suf++;
    }

    int end_i = n - suf;
    int end_j = m - suf;

    // Middle segments: [i, end_i) and [j, end_j)
    int midN = end_i - i;
    int midM = end_j - j;

    if (midN > 0 && midM > 0) {
        // Parameters adaptive to size
        int K;
        if (max(midN, midM) < 200) K = 4;
        else if (max(midN, midM) < 1000) K = 8;
        else K = 16;

        int MIN_ANCHOR = max(4 * K, 32);
        if (max(midN, midM) > 2000000) MIN_ANCHOR = max(MIN_ANCHOR, 128);
        if (max(midN, midM) > 8000000) MIN_ANCHOR = max(MIN_ANCHOR, 192);

        int STEP;
        if (max(midN, midM) < 100000) STEP = 8;
        else if (max(midN, midM) < 1000000) STEP = 32;
        else if (max(midN, midM) < 5000000) STEP = 64;
        else STEP = 128;

        int DIAG_SLACK = STEP * 64; // tolerance on diagonal drift
        const int MAX_STORE_PER_KEY = 4;
        const int CAND_LIMIT_PER_POS = 4;

        // Build anchor map from S2 middle sampled k-grams
        unordered_map<uint64_t, vector<int>> mp;
        int est = (end_j - j - K >= 0) ? ((end_j - j - K) / STEP + 4) : 4;
        mp.reserve((size_t)est * 2);

        if (end_j - j >= K) {
            for (int pos = j; pos <= end_j - K; pos += STEP) {
                uint64_t h = fnv1a_hash(b, pos, K);
                auto &v = mp[h];
                if ((int)v.size() < MAX_STORE_PER_KEY) v.push_back(pos);
            }
        }

        // Greedy chaining of anchors
        int cur_i = i, cur_j = j;
        int scan_p = cur_i;
        while (scan_p <= end_i - K) {
            uint64_t h = fnv1a_hash(a, scan_p, K);
            auto it = mp.find(h);
            bool anchored = false;
            if (it != mp.end()) {
                auto &v = it->second;
                int candChecked = 0;
                // Prefer candidates whose diagonal is close
                // We'll sort candidates by |(j0 - scan_p) - (cur_j - cur_i)| increasing (but small v, so simple)
                array<pair<int,int>, 8> tmp{};
                int tcnt = 0;
                for (int j0 : v) {
                    if (j0 < j || j0 > end_j - K) continue;
                    long long dcur = (long long)cur_j - (long long)cur_i;
                    long long dnew = (long long)j0 - (long long)scan_p;
                    long long d = llabs(dnew - dcur);
                    if (d <= (long long)DIAG_SLACK) {
                        if (tcnt < (int)tmp.size()) tmp[tcnt++] = { (int)d, j0 };
                    }
                }
                if (tcnt > 1) {
                    sort(tmp.begin(), tmp.begin() + tcnt, [](const pair<int,int>& A, const pair<int,int>& B){
                        return A.first < B.first;
                    });
                }
                for (int idx = 0; idx < tcnt && candChecked < CAND_LIMIT_PER_POS; ++idx, ++candChecked) {
                    int j0 = tmp[idx].second;
                    if (j0 < cur_j) continue;

                    // Extend left/right
                    int ii = scan_p, jj = j0;
                    while (ii > cur_i && jj > cur_j && a[ii - 1] == b[jj - 1]) { ii--; jj--; }
                    int ii2 = scan_p + K, jj2 = j0 + K;
                    while (ii2 < end_i && jj2 < end_j && a[ii2] == b[jj2]) { ii2++; jj2++; }

                    int L = ii2 - ii;
                    if (L >= MIN_ANCHOR) {
                        // Emit ops to reach anchor start
                        align_gap(res, cur_i, cur_j, ii, jj);
                        // Emit anchor matches
                        res.append((size_t)L, 'M');
                        cur_i += L;
                        cur_j += L;
                        scan_p = cur_i; // continue scanning from end of anchor
                        anchored = true;
                        break;
                    }
                }
            }
            if (!anchored) {
                scan_p += STEP;
            }
        }
        // Align leftover gap before suffix
        align_gap(res, i, j, end_i, end_j);
    } else {
        // If one side is empty in the middle
        if (midN > 0 && midM == 0) {
            res.append((size_t)midN, 'D');
            i += midN;
        } else if (midM > 0 && midN == 0) {
            res.append((size_t)midM, 'I');
            j += midM;
        }
    }

    // Common suffix
    res.append((size_t)suf, 'M');

    // If any remaining (due to edge conditions), align naively
    // This ensures validity even if something went off in anchors
    if (i < n || j < m) {
        int rem_i = n - i;
        int rem_j = m - j;
        if (rem_i > rem_j) {
            res.append((size_t)(rem_i - rem_j), 'D');
            i += (rem_i - rem_j);
        } else if (rem_j > rem_i) {
            res.append((size_t)(rem_j - rem_i), 'I');
            j += (rem_j - rem_i);
        }
        int k = min(n - i, m - j);
        if (k > 0) {
            res.append((size_t)k, 'M');
            i += k; j += k;
        }
    }

    // As a final safeguard, if still mismatched, fill with deletions or insertions
    if (i < n) res.append((size_t)(n - i), 'D');
    if (j < m) res.append((size_t)(m - j), 'I');

    cout << res << '\n';
    return 0;
}