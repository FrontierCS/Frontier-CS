#include <bits/stdc++.h>
using namespace std;

static void printVec(const vector<int>& v) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << '\n';
}

template <class Transform>
static vector<int> extractLIS(const vector<int>& idxs, const vector<int>& perm, int n, Transform transform) {
    if (idxs.empty()) return {};

    vector<long long> tailVal;
    vector<int> tailIdx;
    tailVal.reserve(idxs.size());
    tailIdx.reserve(idxs.size());

    vector<int> par(n + 1, -1);

    for (int idx : idxs) {
        long long v = transform(perm[idx]);
        int pos = (int)(lower_bound(tailVal.begin(), tailVal.end(), v) - tailVal.begin());
        int prev = (pos > 0 ? tailIdx[pos - 1] : -1);

        if (pos == (int)tailVal.size()) {
            tailVal.push_back(v);
            tailIdx.push_back(idx);
        } else {
            tailVal[pos] = v;
            tailIdx[pos] = idx;
        }
        par[idx] = prev;
    }

    vector<int> res;
    int cur = tailIdx.back();
    while (cur != -1) {
        res.push_back(cur);
        cur = par[cur];
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> p(n + 1);
    for (int i = 1; i <= n; i++) cin >> p[i];

    vector<int> group(n + 1, -1);

    vector<int> remaining;
    remaining.reserve(n);
    for (int i = 1; i <= n; i++) remaining.push_back(i);

    auto id = [&](int x) -> int { return x; };
    auto dec = [&](int x) -> int { return (n + 1 - x); };

    auto markAndRemove = [&](const vector<int>& picked, int g) {
        for (int idx : picked) group[idx] = g;
        vector<int> next;
        next.reserve(remaining.size() - picked.size());
        for (int idx : remaining) if (group[idx] == -1) next.push_back(idx);
        remaining.swap(next);
    };

    // a: take one LIS
    {
        auto picked = extractLIS(remaining, p, n, id);
        markAndRemove(picked, 0);
    }
    // c: take another LIS
    {
        auto picked = extractLIS(remaining, p, n, id);
        markAndRemove(picked, 2);
    }
    // b: take one LDS (LIS on transformed values)
    {
        auto picked = extractLIS(remaining, p, n, dec);
        markAndRemove(picked, 1);
    }
    // d: take another LDS
    {
        auto picked = extractLIS(remaining, p, n, dec);
        markAndRemove(picked, 3);
    }

    // Put all leftovers into a
    for (int idx : remaining) group[idx] = 0;

    vector<int> a, b, c, d;
    a.reserve(n);
    b.reserve(n);
    c.reserve(n);
    d.reserve(n);

    for (int i = 1; i <= n; i++) {
        int g = group[i];
        if (g == 0) a.push_back(p[i]);
        else if (g == 1) b.push_back(p[i]);
        else if (g == 2) c.push_back(p[i]);
        else d.push_back(p[i]);
    }

    cout << a.size() << ' ' << b.size() << ' ' << c.size() << ' ' << d.size() << "\n";
    printVec(a);
    printVec(b);
    printVec(c);
    printVec(d);

    return 0;
}