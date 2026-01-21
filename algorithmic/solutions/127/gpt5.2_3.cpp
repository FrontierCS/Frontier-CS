#include <bits/stdc++.h>
using namespace std;

struct Resp {
    int a0, a1;
};

static int n;
static vector<char> asked, isOne;
static vector<int> a0v, a1v, sumv;

static void answer(int idx) {
    cout << "! " << idx << "\n" << flush;
    exit(0);
}

static Resp ask(int i) {
    if (i < 0 || i >= n) exit(0);
    if (asked[i]) return {a0v[i], a1v[i]};
    cout << "? " << i << "\n" << flush;
    int x, y;
    if (!(cin >> x >> y)) exit(0);
    asked[i] = 1;
    a0v[i] = x;
    a1v[i] = y;
    sumv[i] = x + y;
    if (sumv[i] == 0) answer(i);
    return {x, y};
}

static inline void markOne(int i, vector<int>& ones) {
    if (i < 0 || i >= n) return;
    if (!isOne[i]) {
        isOne[i] = 1;
        ones.push_back(i);
    }
}

static int findZeroInInterval(int l, int r, int M, vector<int>& ones) {
    // Find an index p in (l, r) such that sum[p] == M (i.e., cheapest type).
    int mid = (l + r) / 2;
    int left = mid;
    int right = mid + 1;

    while (true) {
        if (left > l) {
            ask(left);
            if (sumv[left] == M) return left;
            if (sumv[left] < M) markOne(left, ones);
            --left;
        }
        if (right < r) {
            ask(right);
            if (sumv[right] == M) return right;
            if (sumv[right] < M) markOne(right, ones);
            ++right;
        }
        // Interval guaranteed to contain a zero if called appropriately.
        if (left <= l && right >= r) break;
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    if (n <= 0) {
        cout << "! 0\n" << flush;
        return 0;
    }

    asked.assign(n, 0);
    isOne.assign(n, 0);
    a0v.assign(n, 0);
    a1v.assign(n, 0);
    sumv.assign(n, -1);

    vector<int> ones;
    ones.reserve(1024);

    // Phase 1: Query first Q indices to ensure we hit the cheapest type.
    // For n <= 200000, the number of non-cheapest items is < 600, so Q=600 is safe.
    int Q0 = min(n, 600);
    int maxSum = -1;
    int idxMax = 0;

    for (int i = 0; i < Q0; i++) {
        ask(i);
        if (sumv[i] > maxSum) {
            maxSum = sumv[i];
            idxMax = i;
        }
    }

    int M = maxSum;
    if (M < 0) answer(0);

    // Record already discovered non-cheapest indices from initial sampling.
    for (int i = 0; i < Q0; i++) {
        if (sumv[i] < M) markOne(i, ones);
    }

    struct Seg {
        int l, cl; // boundary index l (or -1), and #ones strictly left of l
        int r, cr; // boundary index r (or n), and #ones strictly left of r
    };

    vector<Seg> st;
    st.reserve(10000);
    st.push_back({-1, 0, n, M});

    while (!st.empty()) {
        Seg seg = st.back();
        st.pop_back();

        int len = seg.r - seg.l - 1;
        int onesCnt = seg.cr - seg.cl;
        if (len <= 0 || onesCnt <= 0) continue;

        if (len == onesCnt) {
            // All are ones (non-cheapest).
            for (int i = seg.l + 1; i <= seg.r - 1; i++) markOne(i, ones);
            continue;
        }

        // If there are very few zeros in this segment, brute-force it.
        // (Segment is then small anyway since onesCnt <= M <= ~500.)
        int zerosCnt = len - onesCnt;
        if (len <= 30 || zerosCnt <= 5) {
            for (int i = seg.l + 1; i <= seg.r - 1; i++) {
                ask(i);
                if (sumv[i] < M) markOne(i, ones);
            }
            continue;
        }

        int pivot = findZeroInInterval(seg.l, seg.r, M, ones);
        if (pivot < 0) {
            // Fallback: brute force (shouldn't happen).
            for (int i = seg.l + 1; i <= seg.r - 1; i++) {
                ask(i);
                if (sumv[i] < M) markOne(i, ones);
            }
            continue;
        }

        // pivot is cheapest => a0 is the number of non-cheapest strictly left of pivot
        int cp = a0v[pivot];

        // Recurse on both sides
        st.push_back({pivot, cp, seg.r, seg.cr});
        st.push_back({seg.l, seg.cl, pivot, cp});
    }

    // Phase 3: Among all non-cheapest indices, find the diamond (sum==0).
    for (int idx : ones) {
        if (!asked[idx]) ask(idx); // ask() will terminate if sum==0
        if (sumv[idx] == 0) answer(idx);
    }

    // As required, output something even if not found.
    answer(0);
    return 0;
}