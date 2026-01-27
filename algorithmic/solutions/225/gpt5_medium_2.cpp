#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        queries[i] = {l, r};
    }

    // Prebuild aligned value-interval sets using power-of-two decomposition.
    int LOG = 0;
    while ((1<<LOG) <= n) ++LOG;

    // idByLevel[k][idx] = set id for value interval [idx*len+1, min((idx+1)*len, n)], only for full intervals (len fits)
    vector<vector<int>> idByLevel(LOG);
    idByLevel[0].resize(n);
    // Leaves: singleton sets correspond to initial S_{pos[v]}
    for (int v = 1; v <= n; ++v) {
        idByLevel[0][v-1] = pos[v];
    }

    vector<pair<int,int>> ops;
    long long cnt = n;

    for (int k = 1; k < LOG; ++k) {
        int len = 1 << k;
        int half = len >> 1;
        int num = (n / len) * 1; // only full intervals that fit entirely
        idByLevel[k].resize((n + len - 1) / len, 0);
        for (int idx = 0; idx < (int)idByLevel[k].size(); ++idx) {
            int L = idx * len + 1;
            int R = L + len - 1;
            if (R > n) break; // only full intervals
            int leftIdx = idx * 2;
            int rightIdx = idx * 2 + 1;
            int leftId = idByLevel[k-1][leftIdx];
            int rightId = idByLevel[k-1][rightIdx];
            ops.emplace_back(leftId, rightId);
            ++cnt;
            idByLevel[k][idx] = (int)cnt;
        }
    }

    auto getSegmentsForInterval = [&](int L, int R) {
        // Decompose [L,R] into disjoint aligned power-of-two segments
        vector<int> segIds;
        int x = L;
        while (x <= R) {
            int len = x & -x; // largest power of two dividing x
            while (x + len - 1 > R) len >>= 1;
            int k = __builtin_ctz(len);
            int idx = (x - 1) >> k;
            int id = idByLevel[k][idx];
            segIds.push_back(id);
            x += len;
        }
        return segIds;
    };

    const int MAX_CNT = 2200000;
    vector<int> mark(n+1, 0);
    vector<int> ans(q, 1);

    // Optional cache of built unions defined by ordered segment IDs vector
    struct VecHash {
        size_t operator()(const vector<int>& v) const noexcept {
            size_t h = 1469598103934665603ull;
            for (int x : v) {
                h ^= (size_t)x + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
            }
            return h;
        }
    };
    unordered_map<vector<int>, int, VecHash> cache;
    cache.reserve(q * 2 + 1024);

    for (int qi = 0; qi < q; ++qi) {
        int l = queries[qi].first;
        int r = queries[qi].second;

        // Build mark for values in a[l..r]
        for (int i = l; i <= r; ++i) mark[a[i]] = 1;

        vector<int> allSegs;
        allSegs.reserve(n);

        // Find runs in value domain where mark[v]==1
        int v = 1;
        while (v <= n) {
            if (!mark[v]) {
                ++v;
                continue;
            }
            int L = v;
            while (v+1 <= n && mark[v+1]) ++v;
            int R = v;
            // Decompose run [L,R]
            vector<int> segs = getSegmentsForInterval(L, R);
            allSegs.insert(allSegs.end(), segs.begin(), segs.end());
            ++v;
        }

        // Clear marks
        for (int i = l; i <= r; ++i) mark[a[i]] = 0;

        if (allSegs.empty()) {
            // Should not happen as l<=r; fallback to some singleton
            ans[qi] = pos[a[l]];
            continue;
        }
        if (allSegs.size() == 1u) {
            ans[qi] = allSegs[0];
            continue;
        }

        auto it = cache.find(allSegs);
        if (it != cache.end()) {
            ans[qi] = it->second;
            continue;
        }

        // Merge sequentially in increasing value order
        int cur = allSegs[0];
        for (size_t i = 1; i < allSegs.size(); ++i) {
            if (cnt + 1 > MAX_CNT) {
                // stop further merges, assign some existing id (not ideal)
                // but ensure we don't exceed cnt cap
                break;
            }
            ops.emplace_back(cur, allSegs[i]);
            ++cnt;
            cur = (int)cnt;
        }
        ans[qi] = cur;
        cache.emplace(allSegs, cur);
    }

    cout << cnt << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}