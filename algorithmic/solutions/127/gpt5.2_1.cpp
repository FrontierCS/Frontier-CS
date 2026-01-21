#include <bits/stdc++.h>
using namespace std;

struct Resp {
    bool asked = false;
    int a0 = -1, a1 = -1;
    int total = -1;
};

static int n;
static int rCheapest = -1;
static vector<Resp> respv;
static vector<unsigned char> isNonCheapest;
static vector<int> nonCheapestList;

static void answer(int idx) {
    cout << "! " << idx << "\n" << flush;
    exit(0);
}

static Resp& ask(int i) {
    if (i < 0) i = 0;
    if (i >= n) i = n - 1;
    Resp &r = respv[i];
    if (r.asked) return r;

    cout << "? " << i << "\n" << flush;

    int a0, a1;
    if (!(cin >> a0 >> a1)) {
        // If interaction fails, output arbitrary answer as required.
        answer(0);
    }

    r.asked = true;
    r.a0 = a0;
    r.a1 = a1;
    r.total = a0 + a1;

    if (a0 == 0 && a1 == 0) {
        answer(i);
    }
    return r;
}

static inline void markNonCheapest(int i) {
    if (!isNonCheapest[i]) {
        isNonCheapest[i] = 1;
        nonCheapestList.push_back(i);
    }
}

static inline bool isCheapestIndex(int i) {
    Resp &ri = ask(i);
    if (ri.total == rCheapest) return true;
    markNonCheapest(i);
    return false;
}

static int findCheapestPivot(int L, int R, int cnt) {
    // Find an index p in [L, R) that is of the cheapest type.
    // For cnt < (R-L), scanning cnt+1 distinct positions is guaranteed to hit a cheapest index.
    int len = R - L;
    if (len <= 0) return -1;

    int need = min(cnt + 1, len);
    int mid = (L + R) >> 1;

    vector<int> cand;
    cand.reserve(need + 2);

    int d = 0;
    while ((int)cand.size() < need && (mid - d >= L || mid + d < R)) {
        if (mid - d >= L) cand.push_back(mid - d);
        if (d > 0 && (int)cand.size() < need && mid + d < R) cand.push_back(mid + d);
        d++;
    }

    for (int idx : cand) {
        if (isCheapestIndex(idx)) return idx;
    }

    // Fallback: should not happen if cnt < len and counts are consistent.
    for (int i = L; i < R; i++) {
        if (isCheapestIndex(i)) return i;
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) {
        return 0;
    }

    respv.assign(n, Resp());
    isNonCheapest.assign(n, 0);

    // Step 1: deterministically find the cheapest type's total "more expensive" count rCheapest.
    // Non-cheapest count r is always < 2*sqrt(n) under given constraints, so sampling > that guarantees a cheapest exists.
    int S = (int)floor(2.0L * sqrt((long double)n) + 20.0L);
    if (S > n) S = n;
    if (S < 1) S = 1;

    int bestIdx = 0;
    int bestTotal = -1;
    for (int i = 0; i < S; i++) {
        Resp &ri = ask(i);
        if (ri.total > bestTotal) {
            bestTotal = ri.total;
            bestIdx = i;
        }
    }

    rCheapest = bestTotal;
    if (rCheapest < 0) {
        answer(0);
    }

    // Classify already-queried indices in prefix sample
    for (int i = 0; i < S; i++) {
        if (respv[i].asked && respv[i].total != rCheapest) markNonCheapest(i);
    }

    // If rCheapest == 0, then everything is diamond (impossible), but answer something.
    if (rCheapest == 0) {
        answer(0);
    }

    // Step 2: Use recursive splitting with prefix counts from cheapest indices to locate every non-cheapest index.
    // We'll maintain intervals [L, R) with known counts CL=C(L), CR=C(R).
    struct Node { int L, R, CL, CR; };
    vector<Node> st;
    st.reserve(4096);
    st.push_back({0, n, 0, rCheapest});

    while (!st.empty()) {
        Node cur = st.back();
        st.pop_back();

        int L = cur.L, R = cur.R;
        int CL = cur.CL, CR = cur.CR;

        if (L >= R) continue;
        int cnt = CR - CL;
        int len = R - L;
        if (cnt <= 0) continue;

        if (len == 1) {
            // Single index interval: if cnt==1, it's non-cheapest.
            Resp &ri = ask(L);
            if (ri.total != rCheapest) markNonCheapest(L);
            continue;
        }

        if (cnt == len) {
            // All indices are non-cheapest; brute query them (len <= rCheapest is small).
            for (int i = L; i < R; i++) {
                Resp &ri = ask(i);
                if (ri.total != rCheapest) markNonCheapest(i);
            }
            continue;
        }

        int p = findCheapestPivot(L, R, cnt);
        if (p < 0) {
            // Should not happen; fallback brute within interval (still safe if small, but could be large).
            // We'll do limited brute; if too large, just query midpoint.
            if (len <= 2048) {
                for (int i = L; i < R; i++) {
                    Resp &ri = ask(i);
                    if (ri.total != rCheapest) markNonCheapest(i);
                }
            } else {
                Resp &ri = ask((L + R) >> 1);
                if (ri.total != rCheapest) markNonCheapest((L + R) >> 1);
            }
            continue;
        }

        Resp &rp = ask(p);
        // p must be cheapest here
        int Cp = rp.a0;

        // Left: [L, p)
        if (L < p) st.push_back({L, p, CL, Cp});
        // Right: [p+1, R)
        if (p + 1 < R) st.push_back({p + 1, R, Cp, CR});
    }

    // Step 3: Ensure all discovered non-cheapest indices are checked; diamond must be among them.
    for (int idx : nonCheapestList) {
        ask(idx); // ask() will auto-answer if it's the diamond
    }

    // If not found (shouldn't), output arbitrary index as required.
    answer(0);
    return 0;
}