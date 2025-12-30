#include <bits/stdc++.h>
using namespace std;

struct Res {
    int a0 = -1, a1 = -1, m = -1;
};

static int n;
static int M = -1;
static vector<char> asked;
static vector<Res> memo;

[[noreturn]] static void answer(int idx) {
    cout << "! " << idx << "\n" << flush;
    exit(0);
}

static Res ask(int idx) {
    if (idx < 0) idx = 0;
    if (idx >= n) idx = n - 1;
    if (asked[idx]) return memo[idx];

    cout << "? " << idx << "\n" << flush;

    long long x, y;
    if (!(cin >> x >> y)) {
        cout << "! 0\n" << flush;
        exit(0);
    }
    Res r;
    r.a0 = (int)x;
    r.a1 = (int)y;
    r.m = r.a0 + r.a1;
    memo[idx] = r;
    asked[idx] = 1;

    if (r.m == 0) answer(idx);
    return r;
}

static int upperBoundNonCheapest(int n) {
    // Upper bound on count of all types except the cheapest, given constraints:
    // c_t >= c_{t-1}^2 + 1 and c_v <= n.
    // So c_{v-1} <= floor(sqrt(n-1)), c_{v-2} <= floor(sqrt(c_{v-1}-1)), etc.
    long long x = n;
    long long sum = 1; // diamond
    while (x > 1) {
        long long y = (long long)floor(sqrt((long double)(x - 1)));
        if (y <= 0) break;
        sum += y;
        x = y;
        if (y <= 1) break;
    }
    if (sum > n) sum = n;
    return (int)sum;
}

static int findCheapestInSegment(int L, int R, int k) {
    int len = R - L;
    int limit = min(len, k + 1);
    int mid = (L + R) >> 1;

    vector<int> cand;
    cand.reserve(limit);

    int d = 0;
    while ((int)cand.size() < limit) {
        int p1 = mid - d;
        if (p1 >= L && p1 < R) cand.push_back(p1);
        if ((int)cand.size() == limit) break;
        int p2 = mid + d;
        if (d > 0 && p2 >= L && p2 < R) cand.push_back(p2);
        d++;
        if (d > len) break;
    }

    for (int pos : cand) {
        Res r = ask(pos);
        if (r.m == M) return pos; // confirmed cheapest
    }
    return -1;
}

struct Node {
    int L, R;
    int k;     // number of non-cheapest in [L, R)
    int base;  // number of non-cheapest in [0, L)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    asked.assign(n, 0);
    memo.assign(n, Res());

    int UB = upperBoundNonCheapest(n);
    int K = min(n, UB + 1);

    int bestIdx = 0;
    int bestM = -1;

    for (int i = 0; i < K; i++) {
        Res r = ask(i);
        if (r.m > bestM) {
            bestM = r.m;
            bestIdx = i;
        }
    }

    M = bestM;
    if (M == 0) answer(bestIdx);

    // Ensure bestIdx is indeed cheapest by re-asking (cached) and sanity check.
    {
        Res r = ask(bestIdx);
        (void)r;
    }

    vector<Node> st;
    st.push_back({0, n, M, 0});

    while (!st.empty()) {
        Node cur = st.back();
        st.pop_back();

        if (cur.k == 0 || cur.L >= cur.R) continue;

        int len = cur.R - cur.L;

        // If segment is small relative to number of specials, brute force it.
        if (len <= 2 * cur.k + 5) {
            for (int i = cur.L; i < cur.R; i++) ask(i);
            continue;
        }

        int pivot = findCheapestInSegment(cur.L, cur.R, cur.k);
        if (pivot == -1) {
            // Fallback: brute force (should be rare, indicates something unexpected).
            for (int i = cur.L; i < cur.R; i++) ask(i);
            continue;
        }

        Res pr = ask(pivot);
        if (pr.m != M) {
            // Unexpected; fallback brute.
            for (int i = cur.L; i < cur.R; i++) ask(i);
            continue;
        }

        int globalLeft = pr.a0; // #non-cheapest in [0, pivot)
        int leftK = globalLeft - cur.base;
        if (leftK < 0) leftK = 0;
        if (leftK > cur.k) leftK = cur.k;
        int rightK = cur.k - leftK;

        // Right segment starts at pivot+1; base is #non-cheapest in [0, pivot+1) = globalLeft.
        if (pivot + 1 < cur.R && rightK > 0) st.push_back({pivot + 1, cur.R, rightK, globalLeft});
        if (cur.L < pivot && leftK > 0) st.push_back({cur.L, pivot, leftK, cur.base});
    }

    cout << "! 0\n" << flush;
    return 0;
}