#include <bits/stdc++.h>
using namespace std;

static void appendInt(string &s, long long x) {
    if (x == 0) { s.push_back('0'); return; }
    char buf[32];
    int n = 0;
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = n - 1; i >= 0; --i) s.push_back(buf[i]);
}

struct SetRef {
    const vector<int>* pool = nullptr;
    vector<pair<int,int>> segs; // [l, r)
    vector<int> extra;

    int size() const {
        long long k = (long long)extra.size();
        for (auto [l, r] : segs) k += (r - l);
        return (int)k;
    }
};

static int N, M;
static int L;
static long long Q = 0;
static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

static int askUnion(const SetRef &base,
                    const vector<pair<int,int>> &addSegs,
                    const vector<int> &addExtra) {
    long long k = (long long)base.extra.size() + (long long)addExtra.size();
    for (auto [l, r] : base.segs) k += (r - l);
    for (auto [l, r] : addSegs) k += (r - l);

    string out;
    out.reserve((size_t)k * 7 + 32);
    out.push_back('?');
    out.push_back(' ');
    appendInt(out, k);

    auto &pool = *base.pool;

    for (int x : base.extra) {
        out.push_back(' ');
        appendInt(out, x);
    }
    for (auto [l, r] : base.segs) {
        for (int i = l; i < r; ++i) {
            out.push_back(' ');
            appendInt(out, pool[i]);
        }
    }
    for (int x : addExtra) {
        out.push_back(' ');
        appendInt(out, x);
    }
    for (auto [l, r] : addSegs) {
        for (int i = l; i < r; ++i) {
            out.push_back(' ');
            appendInt(out, pool[i]);
        }
    }
    out.push_back('\n');

    cout << out;
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    ++Q;
    return res;
}

static inline bool coversSeg(const SetRef &base, int l, int r) {
    vector<pair<int,int>> addSegs;
    addSegs.push_back({l, r});
    return askUnion(base, addSegs, {}) >= 1;
}

static inline bool coversExtra(const SetRef &base, const vector<int> &ex) {
    return askUnion(base, {}, ex) >= 1;
}

// Finds an inclusion-minimal subset of pool[l..r) to add to base, so that base+subset covers all colors.
// Precondition: base itself may be false, and base + pool[l..r) is true.
static vector<int> minimizeStick(const SetRef &base, int l, int r) {
    if (r - l == 1) return { (*base.pool)[l] };

    int mid = (l + r) >> 1;

    if (coversSeg(base, l, mid)) {
        return minimizeStick(base, l, mid);
    } else {
        SetRef base2 = base;
        base2.segs.push_back({l, mid});
        vector<int> s2 = minimizeStick(base2, mid, r);

        if (coversExtra(base, s2)) {
            return s2;
        }

        SetRef base3 = base;
        base3.extra.insert(base3.extra.end(), s2.begin(), s2.end());
        vector<int> s1 = minimizeStick(base3, l, mid);

        if (s1.empty()) return s2;
        s1.insert(s1.end(), s2.begin(), s2.end());
        return s1;
    }
}

static void outputStick(const vector<int> &stick) {
    string out;
    out.reserve((size_t)stick.size() * 7 + 8);
    out.push_back('!');
    for (int x : stick) {
        out.push_back(' ');
        appendInt(out, x);
    }
    out.push_back('\n');
    cout << out;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    L = N * M;

    if (N == 1) {
        for (int i = 1; i <= L; ++i) outputStick({i});
        return 0;
    }
    if (M == 1) {
        vector<int> stick;
        stick.reserve(N);
        for (int i = 1; i <= N; ++i) stick.push_back(i);
        outputStick(stick);
        return 0;
    }

    vector<char> used(L + 1, 0);

    for (int rep = 0; rep < M; ++rep) {
        vector<int> pool;
        pool.reserve(L - rep * N);
        for (int i = 1; i <= L; ++i) if (!used[i]) pool.push_back(i);

        if ((int)pool.size() == N) {
            outputStick(pool);
            return 0;
        }

        shuffle(pool.begin(), pool.end(), rng);

        SetRef base;
        base.pool = &pool;

        vector<int> stick = minimizeStick(base, 0, (int)pool.size());

        // Safety fallback (should not happen)
        if ((int)stick.size() != N) {
            vector<int> tmp = stick;
            shuffle(tmp.begin(), tmp.end(), rng);
            SetRef b2;
            b2.pool = &tmp;
            stick = minimizeStick(b2, 0, (int)tmp.size());
        }

        for (int x : stick) used[x] = 1;
        outputStick(stick);
    }

    return 0;
}