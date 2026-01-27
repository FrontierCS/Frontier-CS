#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parseBig(const string& s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (c - '0');
        }
    }
    return x;
}

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

struct Cand {
    vector<uint8_t> b;
    cpp_int sum;
    cpp_int diff;
};

static inline void updateBest(Cand& best, bool& hasBest, const Cand& cand) {
    if (!hasBest || cand.diff < best.diff) {
        best = cand;
        hasBest = true;
    }
}

static Cand greedyImproveAdd(const vector<cpp_int>& a, const cpp_int& W, const vector<int>& order) {
    int n = (int)a.size();
    Cand c;
    c.b.assign(n, 0);
    c.sum = 0;
    c.diff = absDiff(W, c.sum);

    for (int idx : order) {
        const cpp_int& v = a[idx];
        if (v == 0) continue;
        cpp_int newSum = c.sum + v;
        cpp_int newDiff = absDiff(W, newSum);
        if (newDiff < c.diff) {
            c.b[idx] = 1;
            c.sum = std::move(newSum);
            c.diff = std::move(newDiff);
            if (c.diff == 0) break;
        }
    }
    return c;
}

static Cand greedyBelowAdd(const vector<cpp_int>& a, const cpp_int& W, const vector<int>& order) {
    int n = (int)a.size();
    Cand c;
    c.b.assign(n, 0);
    c.sum = 0;

    for (int idx : order) {
        const cpp_int& v = a[idx];
        if (v == 0) continue;
        cpp_int newSum = c.sum + v;
        if (newSum <= W) {
            c.b[idx] = 1;
            c.sum = std::move(newSum);
            if (c.sum == W) break;
        }
    }
    c.diff = absDiff(W, c.sum);
    return c;
}

static Cand greedyRemove(const vector<cpp_int>& a, const cpp_int& W, const vector<int>& order, const cpp_int& totalSum) {
    int n = (int)a.size();
    Cand c;
    c.b.assign(n, 1);
    c.sum = totalSum;
    c.diff = absDiff(W, c.sum);

    for (int idx : order) {
        const cpp_int& v = a[idx];
        if (v == 0) continue;
        cpp_int newSum = c.sum - v;
        cpp_int newDiff = absDiff(W, newSum);
        if (newDiff < c.diff) {
            c.b[idx] = 0;
            c.sum = std::move(newSum);
            c.diff = std::move(newDiff);
            if (c.diff == 0) break;
        }
    }
    return c;
}

static Cand localImprove(const vector<cpp_int>& a, const cpp_int& W, Cand c, mt19937_64& rng, int maxPasses = 2) {
    int n = (int)a.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);

    for (int pass = 0; pass < maxPasses; pass++) {
        bool improved = false;
        shuffle(ord.begin(), ord.end(), rng);

        for (int i : ord) {
            const cpp_int& v = a[i];
            if (v == 0) continue;

            cpp_int newSum;
            if (c.b[i]) {
                newSum = c.sum - v;
            } else {
                newSum = c.sum + v;
            }
            cpp_int newDiff = absDiff(W, newSum);
            if (newDiff < c.diff) {
                c.b[i] ^= 1;
                c.sum = std::move(newSum);
                c.diff = std::move(newDiff);
                improved = true;
                if (c.diff == 0) return c;
            }
        }
        if (!improved) break;
    }
    return c;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Ws;
    if (!(cin >> n >> Ws)) return 0;
    cpp_int W = parseBig(Ws);

    vector<cpp_int> a(n);
    cpp_int totalSum = 0;
    cpp_int M = 0;

    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        a[i] = parseBig(s);
        totalSum += a[i];
        if (a[i] > M) M = a[i];
    }

    // If we can’t reach W, taking everything is optimal (maximizes S).
    if (totalSum <= W) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    vector<int> desc(n), asc(n);
    iota(desc.begin(), desc.end(), 0);
    sort(desc.begin(), desc.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });
    asc = desc;
    reverse(asc.begin(), asc.end());

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    Cand best;
    bool hasBest = false;

    auto consider = [&](Cand c) {
        c = localImprove(a, W, std::move(c), rng, 2);
        updateBest(best, hasBest, c);
    };

    consider(greedyImproveAdd(a, W, desc));
    consider(greedyBelowAdd(a, W, desc));
    consider(greedyImproveAdd(a, W, asc));
    consider(greedyBelowAdd(a, W, asc));
    consider(greedyRemove(a, W, desc, totalSum));
    consider(greedyRemove(a, W, asc, totalSum));

    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.85; // keep some margin
    int it = 0;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        shuffle(ord.begin(), ord.end(), rng);

        Cand c1 = greedyImproveAdd(a, W, ord);
        c1 = localImprove(a, W, std::move(c1), rng, 1);
        updateBest(best, hasBest, c1);

        if ((it & 3) == 0) {
            Cand c2 = greedyRemove(a, W, ord, totalSum);
            c2 = localImprove(a, W, std::move(c2), rng, 1);
            updateBest(best, hasBest, c2);
        }

        if (hasBest && best.diff == 0) break;
        it++;
    }

    if (!hasBest) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << int(best.b[i]);
    }
    cout << '\n';
    return 0;
}