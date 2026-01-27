#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline int readChunk(const string& s, int l, int len) {
    int v = 0;
    for (int i = 0; i < len; i++) v = v * 10 + (s[l + i] - '0');
    return v;
}

static cpp_int parseBig(const string& s) {
    static const int BASE = 1000000000;
    int n = (int)s.size();
    if (n == 0) return 0;
    int first = n % 9;
    if (first == 0) first = 9;
    cpp_int x = readChunk(s, 0, first);
    for (int pos = first; pos < n; pos += 9) {
        x *= BASE;
        x += readChunk(s, pos, 9);
    }
    return x;
}

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

struct Result {
    vector<unsigned char> b;
    cpp_int sum;
    cpp_int diff;
};

static Result runHeuristic(const vector<int>& order, int mode,
                           const vector<cpp_int>& a, const cpp_int& W) {
    int n = (int)a.size();
    vector<unsigned char> b(n, 0);
    cpp_int sum = 0;

    if (mode == 1) { // do not exceed W
        for (int idx : order) {
            cpp_int newSum = sum + a[idx];
            if (newSum <= W) {
                sum = newSum;
                b[idx] = 1;
            }
        }
    } else { // greedy minimize abs diff
        cpp_int curDiff = absDiff(W, sum);
        for (int idx : order) {
            cpp_int newSum = sum + a[idx];
            cpp_int newDiff = absDiff(W, newSum);
            if (newDiff <= curDiff) {
                sum = newSum;
                curDiff = newDiff;
                b[idx] = 1;
            }
        }
    }

    cpp_int diff = absDiff(W, sum);

    // Small local improvement: a couple of add/remove passes
    for (int it = 0; it < 2; it++) {
        bool changed = false;
        for (int i = 0; i < n; i++) {
            if (b[i]) {
                cpp_int newSum = sum - a[i];
                cpp_int newDiff = absDiff(W, newSum);
                if (newDiff < diff) {
                    b[i] = 0;
                    sum = newSum;
                    diff = newDiff;
                    changed = true;
                }
            } else {
                cpp_int newSum = sum + a[i];
                cpp_int newDiff = absDiff(W, newSum);
                if (newDiff < diff) {
                    b[i] = 1;
                    sum = newSum;
                    diff = newDiff;
                    changed = true;
                }
            }
        }
        if (!changed) break;
    }

    return {std::move(b), sum, diff};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string Wstr;
    if (!(cin >> n >> Wstr)) return 0;
    cpp_int W = parseBig(Wstr);

    vector<cpp_int> a(n);
    cpp_int M = 0;
    for (int i = 0; i < n; i++) {
        string s;
        cin >> s;
        a[i] = parseBig(s);
        if (a[i] > M) M = a[i];
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<int> desc = idx;
    stable_sort(desc.begin(), desc.end(), [&](int i, int j) {
        return a[i] > a[j];
    });

    vector<int> asc = idx;
    stable_sort(asc.begin(), asc.end(), [&](int i, int j) {
        return a[i] < a[j];
    });

    vector<int> rnd = idx;
    mt19937_64 rng(123456789);
    shuffle(rnd.begin(), rnd.end(), rng);

    Result best = runHeuristic(desc, 0, a, W);
    {
        Result r = runHeuristic(desc, 1, a, W);
        if (r.diff < best.diff) best = std::move(r);
    }
    {
        Result r = runHeuristic(asc, 0, a, W);
        if (r.diff < best.diff) best = std::move(r);
    }
    {
        Result r = runHeuristic(rnd, 0, a, W);
        if (r.diff < best.diff) best = std::move(r);
    }

    for (int i = 0; i < n; i++) {
        cout << int(best.b[i]) << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}