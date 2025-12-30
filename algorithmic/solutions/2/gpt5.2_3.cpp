#include <bits/stdc++.h>
#include <charconv>
using namespace std;

static inline void appendInt(string &s, int x) {
    char buf[16];
    auto [ptr, ec] = std::to_chars(buf, buf + 16, x);
    s.append(buf, ptr);
}

struct Interactor {
    int n;
    long long queries = 0;

    explicit Interactor(int n_) : n(n_) {}

    int ask(const vector<int> &a) {
        ++queries;
        string s;
        s.reserve(4 + n * 5);
        s.push_back('0');
        s.push_back(' ');
        for (int i = 0; i < n; i++) {
            appendInt(s, a[i]);
            s.push_back(i + 1 == n ? '\n' : ' ');
        }
        cout.write(s.data(), (streamsize)s.size());
        cout.flush();

        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        return x;
    }

    [[noreturn]] void answer(const vector<int> &p) {
        string s;
        s.reserve(4 + n * 5);
        s.push_back('1');
        s.push_back(' ');
        for (int i = 0; i < n; i++) {
            appendInt(s, p[i]);
            s.push_back(i + 1 == n ? '\n' : ' ');
        }
        cout.write(s.data(), (streamsize)s.size());
        cout.flush();
        exit(0);
    }
};

static inline int ceil_log2_int(int x) {
    int k = 0;
    int p = 1;
    while (p < x) {
        p <<= 1;
        k++;
    }
    return k;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it(n);

    if (n == 1) {
        it.answer(vector<int>{1});
    }

    long long searchQueries = 0;
    for (int m = 1; m <= n; m++) searchQueries += ceil_log2_int(m);

    long long budgetForDerangement = 9999 - searchQueries;
    if (budgetForDerangement < 1) budgetForDerangement = 1;
    int maxTries = (int)min<long long>(1000, budgetForDerangement);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> base(n);
    iota(base.begin(), base.end(), 1);

    vector<int> q0;
    bool found = false;

    for (int t = 0; t < maxTries; t++) {
        shuffle(base.begin(), base.end(), rng);
        int x = it.ask(base);
        if (x == 0) {
            q0 = base;
            found = true;
            break;
        }
    }
    if (!found) {
        // Extremely unlikely; keep trying (may exceed the scoring baseline, but preserves correctness)
        for (int t = maxTries; t < 5000; t++) {
            shuffle(base.begin(), base.end(), rng);
            int x = it.ask(base);
            if (x == 0) {
                q0 = base;
                found = true;
                break;
            }
        }
    }
    if (!found) exit(0);

    vector<int> rem(n);
    iota(rem.begin(), rem.end(), 0);
    vector<int> ans(n, 0);

    for (int v = 1; v <= n; v++) {
        int m = (int)rem.size();
        if (m == 1) {
            ans[rem[0]] = v;
            rem.clear();
            break;
        }

        int l = 0, r = m;
        while (r - l > 1) {
            int mid = (l + r) >> 1;
            vector<int> q = q0;
            for (int idx = l; idx < mid; idx++) q[rem[idx]] = v;
            int x = it.ask(q);
            if (x == 1) r = mid;
            else l = mid;
        }
        int pos = rem[l];
        ans[pos] = v;
        rem.erase(rem.begin() + l);
    }

    it.answer(ans);
}