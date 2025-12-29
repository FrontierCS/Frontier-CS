#include <bits/stdc++.h>
using namespace std;

struct Ans {
    int a0, a1;
};

static int n;
static vector<Ans> resv;
static vector<unsigned char> asked;
static vector<unsigned char> isExp;
static vector<int> expList;
static int M = -1;

static void finish(int idx) {
    cout << "! " << idx << "\n";
    cout.flush();
    exit(0);
}

static Ans ask(int i) {
    if (i < 0 || i >= n) return {-1, -1};
    if (asked[i]) return resv[i];
    cout << "? " << i << "\n";
    cout.flush();
    int a0, a1;
    if (!(cin >> a0 >> a1)) exit(0);
    asked[i] = 1;
    resv[i] = {a0, a1};
    if (a0 == 0 && a1 == 0) finish(i);
    return resv[i];
}

static inline void markExpensive(int i) {
    if (i < 0 || i >= n) return;
    if (!isExp[i]) {
        isExp[i] = 1;
        expList.push_back(i);
    }
}

static pair<int,int> findCheapInInterval(int target, int l, int r) {
    if (l > r) return {-1, -1};
    target = max(l, min(r, target));
    int len = r - l;
    for (int off = 0; off <= len; off++) {
        int p1 = target - off;
        if (p1 >= l && p1 <= r) {
            Ans an = ask(p1);
            int B = an.a0 + an.a1;
            if (B == M) return {p1, an.a0};
            markExpensive(p1);
        }
        int p2 = target + off;
        if (off > 0 && p2 >= l && p2 <= r) {
            Ans an = ask(p2);
            int B = an.a0 + an.a1;
            if (B == M) return {p2, an.a0};
            markExpensive(p2);
        }
    }
    // Fallback brute (should be unnecessary)
    for (int p = l; p <= r; p++) {
        Ans an = ask(p);
        int B = an.a0 + an.a1;
        if (B == M) return {p, an.a0};
        markExpensive(p);
    }
    return {l, 0};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    resv.assign(n, {INT_MIN, INT_MIN});
    asked.assign(n, 0);
    isExp.assign(n, 0);

    // Initial probing: K = min(n, 512), evenly spaced indices
    int K = min(n, 512);
    vector<int> initIdx;
    initIdx.reserve(K);
    if (K == n) {
        for (int i = 0; i < n; i++) initIdx.push_back(i);
    } else {
        for (int j = 0; j < K; j++) {
            long long idx = (long long)j * (n - 1) / (K - 1);
            if (initIdx.empty() || initIdx.back() != (int)idx) initIdx.push_back((int)idx);
        }
        // Ensure exactly K distinct indices if possible
        vector<unsigned char> used(n, 0);
        for (int x : initIdx) used[x] = 1;
        for (int i = 0; (int)initIdx.size() < K && i < n; i++) {
            if (!used[i]) {
                used[i] = 1;
                initIdx.push_back(i);
            }
        }
        sort(initIdx.begin(), initIdx.end());
        initIdx.erase(unique(initIdx.begin(), initIdx.end()), initIdx.end());
        // If still less than K (can only happen if n<K, but K<=n), ignore.
    }

    int maxB = -1;
    for (int idx : initIdx) {
        Ans an = ask(idx);
        int B = an.a0 + an.a1;
        maxB = max(maxB, B);
    }
    if (maxB < 0) {
        finish(0);
    }
    M = maxB;

    // Collect cheapest probes (B == M) and mark already known expensive (B < M)
    vector<pair<int,int>> probes; // (pos, F=expensive-left)
    probes.reserve(initIdx.size());
    for (int idx : initIdx) {
        Ans an = resv[idx];
        int B = an.a0 + an.a1;
        if (B == M) probes.push_back({idx, an.a0});
        else if (B < M) markExpensive(idx);
    }

    if (probes.empty()) {
        // Should not happen if M is correct, but fallback: try to find a cheap position
        auto p = findCheapInInterval((n - 1) / 2, 0, n - 1);
        if (p.first >= 0) probes.push_back({p.first, p.second});
        else finish(0);
    }

    sort(probes.begin(), probes.end());
    probes.erase(unique(probes.begin(), probes.end()), probes.end());

    // Build known points (pos, F). Add virtual boundaries -1 with F=0 and n with F=M.
    vector<pair<int,int>> pts;
    pts.reserve(probes.size() + 2);
    pts.push_back({-1, 0});
    for (auto &pr : probes) pts.push_back(pr);
    pts.push_back({n, M});
    sort(pts.begin(), pts.end());
    // Deduplicate by position (keep the first; they should match anyway)
    {
        vector<pair<int,int>> tmp;
        tmp.reserve(pts.size());
        for (auto &p : pts) {
            if (tmp.empty() || tmp.back().first != p.first) tmp.push_back(p);
        }
        pts.swap(tmp);
    }

    struct Interval {
        int L, R;
        int FL, FR;
    };

    const int BRUTE = 14;
    vector<Interval> st;
    st.reserve(10000);

    for (int i = 0; i + 1 < (int)pts.size(); i++) {
        int L = pts[i].first, R = pts[i+1].first;
        int FL = pts[i].second, FR = pts[i+1].second;
        if (L < R) st.push_back({L, R, FL, FR});
    }

    while (!st.empty()) {
        Interval cur = st.back();
        st.pop_back();
        int L = cur.L, R = cur.R, FL = cur.FL, FR = cur.FR;
        int len = R - L - 1;
        int d = FR - FL;
        if (d <= 0 || len <= 0) continue;

        if (d == len) {
            for (int pos = L + 1; pos <= R - 1; pos++) markExpensive(pos);
            continue;
        }

        if (len <= BRUTE) {
            for (int pos = L + 1; pos <= R - 1; pos++) {
                Ans an = ask(pos);
                int B = an.a0 + an.a1;
                if (B < M) markExpensive(pos);
            }
            continue;
        }

        int target = (L + R) / 2;
        target = max(L + 1, min(R - 1, target));

        auto mid = findCheapInInterval(target, L + 1, R - 1);
        int midPos = mid.first;
        int Fmid = mid.second;

        if (midPos <= L || midPos >= R) {
            // Fallback: brute
            for (int pos = L + 1; pos <= R - 1; pos++) {
                Ans an = ask(pos);
                int B = an.a0 + an.a1;
                if (B < M) markExpensive(pos);
            }
            continue;
        }

        // Split
        st.push_back({L, midPos, FL, Fmid});
        st.push_back({midPos, R, Fmid, FR});
    }

    // Query all discovered non-cheapest indices until diamond found.
    for (int pos : expList) {
        Ans an = ask(pos);
        if (an.a0 == 0 && an.a1 == 0) finish(pos);
    }

    // As an extra safety, if we somehow missed, try a few more queries around.
    for (int i = 0; i < min(n, 50); i++) {
        Ans an = ask(i);
        if (an.a0 == 0 && an.a1 == 0) finish(i);
    }

    finish(0);
    return 0;
}