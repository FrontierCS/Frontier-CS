#include <bits/stdc++.h>
using namespace std;

static constexpr unsigned char START = 0;
static constexpr unsigned char S0_1 = 1;
static constexpr unsigned char S0_2 = 2;
static constexpr unsigned char S1_1 = 3;
static constexpr unsigned char S1_2 = 4;
static constexpr unsigned char ELIM  = 255;

static inline bool canAppend(unsigned char st, int d) {
    if (st == ELIM) return false;
    if (d == 0) return st != S0_2;
    return st != S1_2;
}

static inline unsigned char nextState(unsigned char st, int d) {
    if (st == ELIM) return ELIM;
    if (st == START) return d ? S1_1 : S0_1;
    switch (st) {
        case S0_1: return d == 0 ? S0_2 : S1_1;
        case S0_2: return d == 0 ? ELIM : S1_1;
        case S1_1: return d == 1 ? S1_2 : S0_1;
        case S1_2: return d == 1 ? ELIM : S0_1;
    }
    return ELIM;
}

struct EvalRes {
    int worstSurvivors;
    int secMinRun2; // larger is better
    int split;      // larger is better
    int len;        // smaller is better
    int l, r;
};

static inline bool better(const EvalRes& a, const EvalRes& b) {
    if (a.worstSurvivors != b.worstSurvivors) return a.worstSurvivors < b.worstSurvivors;
    if (a.secMinRun2 != b.secMinRun2) return a.secMinRun2 > b.secMinRun2;
    if (a.split != b.split) return a.split > b.split;
    if (a.len != b.len) return a.len < b.len;
    if (a.l != b.l) return a.l < b.l;
    return a.r < b.r;
}

static inline int getSum(const vector<int>& pre, int l, int r) {
    if (l > r) return 0;
    return pre[r] - pre[l - 1];
}

static pair<int,int> selectInterval(
    int n,
    int activeCount,
    const vector<int>& activeIdx,
    const vector<int>& preA,
    const vector<int>& preS0,
    const vector<int>& preS1,
    const vector<int>& preSt1,
    const vector<int>& preSt3,
    mt19937& rng
) {
    int totA  = preA[n];
    int totS0 = preS0[n];
    int totS1 = preS1[n];
    int totSt1 = preSt1[n];
    int totSt3 = preSt3[n];

    auto eval = [&](int l, int r, EvalRes &best) {
        l = max(1, min(l, n));
        r = max(1, min(r, n));
        if (l > r) swap(l, r);

        int insideA  = getSum(preA, l, r);
        int insideS0 = getSum(preS0, l, r);
        int insideS1 = getSum(preS1, l, r);

        int sizeIfO0 = insideS1 + (totS0 - insideS0); // o=0 => inside needs d=1, outside needs d=0
        int sizeIfO1 = insideS0 + (totS1 - insideS1); // o=1 => inside needs d=0, outside needs d=1
        int worst = max(sizeIfO0, sizeIfO1);

        int insideSt1 = getSum(preSt1, l, r);
        int insideSt3 = getSum(preSt3, l, r);
        int outsideSt1 = totSt1 - insideSt1;
        int outsideSt3 = totSt3 - insideSt3;

        // run2 creations:
        // o=0: inside d=1 => state S1_1 creates run2; outside d=0 => state S0_1 creates run2
        int run2o0 = insideSt3 + outsideSt1;
        // o=1: inside d=0 => S0_1; outside d=1 => S1_1
        int run2o1 = insideSt1 + outsideSt3;

        int sec = min(run2o0, run2o1);
        int split = min(insideA, totA - insideA);

        EvalRes cand{worst, sec, split, r - l + 1, l, r};
        if (better(cand, best)) best = cand;
    };

    EvalRes best{INT_MAX, -1, -1, INT_MAX, 1, n};

    // Always consider full range
    eval(1, n, best);

    if (activeCount == 0) return {1, n};
    if (activeCount == 1) return {activeIdx[0], activeIdx[0]};

    // Deterministic candidates around quantiles
    int mid = activeIdx[activeCount / 2];
    eval(1, mid, best);
    eval(mid, n, best);
    eval(mid, mid, best);

    int q1 = activeIdx[activeCount / 4];
    int q3 = activeIdx[(3 * activeCount) / 4];
    eval(q1, q3, best);
    eval(activeIdx[0], mid, best);
    eval(mid, activeIdx.back(), best);

    // Window around median
    {
        int w = max(1, activeCount / 8);
        int iL = max(0, activeCount / 2 - w);
        int iR = min(activeCount - 1, activeCount / 2 + w);
        eval(activeIdx[iL], activeIdx[iR], best);
    }

    // For small activeCount, enumerate all intervals with endpoints at active indices
    if (activeCount <= 450) {
        for (int i = 0; i < activeCount; i++) {
            for (int j = i; j < activeCount; j++) {
                eval(activeIdx[i], activeIdx[j], best);
            }
        }
        // also prefixes and suffixes snapped to active endpoints
        for (int j = 0; j < activeCount; j++) {
            eval(1, activeIdx[j], best);
            eval(activeIdx[j], n, best);
        }
        return {best.l, best.r};
    }

    // Random sampling among active endpoints and random windows
    uniform_int_distribution<int> dist(0, activeCount - 1);
    for (int k = 0; k < 60; k++) {
        int a = activeIdx[dist(rng)];
        int b = activeIdx[dist(rng)];
        eval(min(a, b), max(a, b), best);
    }
    uniform_int_distribution<int> distN(1, n);
    for (int k = 0; k < 40; k++) {
        int c = activeIdx[dist(rng)];
        int rad = distN(rng) % (max(2, n / 3) + 1);
        int l = max(1, c - rad);
        int r = min(n, c + rad);
        eval(l, r, best);
    }

    // Some fixed-ish splits
    eval(1, n / 2, best);
    eval(n / 2 + 1, n, best);
    eval(n / 3, (2 * n) / 3, best);

    return {best.l, best.r};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 1; tc <= t; tc++) {
        int n;
        cin >> n;

        vector<unsigned char> st(n + 1, START);
        int activeCount = n;

        long double base = 1.116L;
        int q = (int)ceill(log((long double)n) / log(base) - 1e-12L);
        int maxQ = 2 * q;

        mt19937 rng((uint32_t)(712367u ^ (uint32_t)(tc * 1000003u) ^ (uint32_t)(n * 19260817u)));

        int queries = 0;
        while (activeCount > 2 && queries < maxQ) {
            vector<int> preA(n + 1, 0), preS0(n + 1, 0), preS1(n + 1, 0), preSt1(n + 1, 0), preSt3(n + 1, 0);
            vector<int> activeIdx;
            activeIdx.reserve(activeCount);

            int cnt = 0;
            for (int i = 1; i <= n; i++) {
                bool act = (st[i] != ELIM);
                preA[i] = preA[i - 1] + (act ? 1 : 0);
                preSt1[i] = preSt1[i - 1] + ((st[i] == S0_1) ? 1 : 0);
                preSt3[i] = preSt3[i - 1] + ((st[i] == S1_1) ? 1 : 0);

                if (act) {
                    cnt++;
                    activeIdx.push_back(i);
                    preS0[i] = preS0[i - 1] + (canAppend(st[i], 0) ? 1 : 0);
                    preS1[i] = preS1[i - 1] + (canAppend(st[i], 1) ? 1 : 0);
                } else {
                    preS0[i] = preS0[i - 1];
                    preS1[i] = preS1[i - 1];
                }
            }
            activeCount = cnt;
            if (activeCount <= 2) break;

            auto [l, r] = selectInterval(n, activeCount, activeIdx, preA, preS0, preS1, preSt1, preSt3, rng);

            cout << "? " << l << " " << r << "\n";
            cout.flush();

            int x;
            if (!(cin >> x)) return 0;
            if (x == -1) return 0;

            int len = r - l + 1;
            int o = (x == len - 1) ? 1 : 0;

            for (int i = 1; i <= n; i++) {
                if (st[i] == ELIM) continue;
                int b = (l <= i && i <= r) ? 1 : 0;
                int d = o ^ b;
                unsigned char ns = nextState(st[i], d);
                if (ns == ELIM) {
                    st[i] = ELIM;
                    activeCount--;
                } else {
                    st[i] = ns;
                }
            }

            queries++;
        }

        vector<int> candidates;
        candidates.reserve(3);
        for (int i = 1; i <= n; i++) if (st[i] != ELIM) candidates.push_back(i);

        if ((int)candidates.size() > 2) {
            // Shouldn't happen; fall back to first two to avoid extra marks.
            candidates.resize(2);
        } else if (candidates.empty()) {
            // Extremely unlikely; arbitrary.
            candidates.push_back(1);
        }

        int marks = 0;
        bool ok = false;
        for (int i = 0; i < (int)candidates.size() && marks < 2; i++) {
            int a = candidates[i];
            cout << "! " << a << "\n";
            cout.flush();

            int y;
            if (!(cin >> y)) return 0;
            if (y == -1) return 0;
            marks++;
            if (y == 1) {
                ok = true;
                break;
            }
        }

        // End this test case
        cout << "#\n";
        cout.flush();
        (void)ok;
    }
    return 0;
}