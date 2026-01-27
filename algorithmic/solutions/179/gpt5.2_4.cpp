#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parseBig(const string& s) {
    static uint32_t pow10[10] = {0};
    if (pow10[0] == 0) {
        pow10[0] = 1;
        for (int i = 1; i <= 9; i++) pow10[i] = pow10[i - 1] * 10u;
    }

    cpp_int x = 0;
    uint32_t chunk = 0;
    int clen = 0;
    for (char ch : s) {
        chunk = chunk * 10u + (uint32_t)(ch - '0');
        clen++;
        if (clen == 9) {
            x *= 1000000000u;
            x += chunk;
            chunk = 0;
            clen = 0;
        }
    }
    if (clen) {
        x *= pow10[clen];
        x += chunk;
    }
    return x;
}

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    if (a >= b) return a - b;
    return b - a;
}

struct Candidate {
    cpp_int sum;
    vector<unsigned char> sel; // 0/1
};

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

    vector<unsigned char> bestSel(n, 0);
    cpp_int bestSum = 0;
    cpp_int bestDiff = absDiff(W, bestSum);
    auto consider = [&](const vector<unsigned char>& sel, const cpp_int& sum) {
        cpp_int d = absDiff(W, sum);
        if (d < bestDiff) {
            bestDiff = d;
            bestSum = sum;
            bestSel = sel;
        }
    };

    auto considerSingle = [&]() {
        for (int i = 0; i < n; i++) {
            cpp_int d = absDiff(W, a[i]);
            if (d < bestDiff) {
                vector<unsigned char> sel(n, 0);
                sel[i] = 1;
                bestDiff = d;
                bestSum = a[i];
                bestSel.swap(sel);
            }
        }
    };

    auto greedyBounded = [&](const vector<int>& ord) -> Candidate {
        Candidate c;
        c.sum = 0;
        c.sel.assign(n, 0);
        for (int idx : ord) {
            cpp_int tmp = c.sum;
            tmp += a[idx];
            if (tmp <= W) {
                c.sum = tmp;
                c.sel[idx] = 1;
            }
        }
        return c;
    };

    auto greedyHill = [&](const vector<int>& ord) -> Candidate {
        Candidate c;
        c.sum = 0;
        c.sel.assign(n, 0);
        cpp_int curDiff = absDiff(W, c.sum);

        for (int idx : ord) {
            cpp_int tmpSum = c.sum;
            tmpSum += a[idx];
            cpp_int newDiff = absDiff(W, tmpSum);
            if (newDiff < curDiff) {
                c.sum = tmpSum;
                c.sel[idx] = 1;
                curDiff = newDiff;
                if (curDiff == 0) break;
            }
        }
        return c;
    };

    auto localSearch = [&](Candidate& c) {
        cpp_int curDiff = absDiff(W, c.sum);
        for (int iter = 0; iter < 3; iter++) {
            cpp_int bestLocalDiff = curDiff;
            int bestI = -1;
            int bestType = 0; // 1 add, -1 remove

            for (int i = 0; i < n; i++) {
                if (!c.sel[i]) {
                    cpp_int tmp = c.sum;
                    tmp += a[i];
                    cpp_int d = absDiff(W, tmp);
                    if (d < bestLocalDiff) {
                        bestLocalDiff = d;
                        bestI = i;
                        bestType = 1;
                        if (bestLocalDiff == 0) break;
                    }
                } else {
                    cpp_int tmp = c.sum;
                    tmp -= a[i];
                    cpp_int d = absDiff(W, tmp);
                    if (d < bestLocalDiff) {
                        bestLocalDiff = d;
                        bestI = i;
                        bestType = -1;
                        if (bestLocalDiff == 0) break;
                    }
                }
            }

            if (bestType == 0) break;
            if (bestType == 1) {
                c.sum += a[bestI];
                c.sel[bestI] = 1;
            } else {
                c.sum -= a[bestI];
                c.sel[bestI] = 0;
            }
            curDiff = bestLocalDiff;
            if (curDiff == 0) break;
        }
    };

    // Baselines
    consider(bestSel, bestSum); // empty
    considerSingle();

    vector<int> baseOrd(n);
    iota(baseOrd.begin(), baseOrd.end(), 0);

    vector<int> ordDesc = baseOrd, ordAsc = baseOrd;
    sort(ordDesc.begin(), ordDesc.end(), [&](int i, int j) { return a[i] > a[j]; });
    sort(ordAsc.begin(), ordAsc.end(), [&](int i, int j) { return a[i] < a[j]; });

    auto runOrders = [&](const vector<int>& ord) {
        {
            Candidate c = greedyBounded(ord);
            localSearch(c);
            consider(c.sel, c.sum);
        }
        {
            Candidate c = greedyHill(ord);
            localSearch(c);
            consider(c.sel, c.sum);
        }
    };

    runOrders(ordDesc);
    runOrders(ordAsc);

    // Randomized runs
    std::mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    int iters = 20;
    vector<int> ord = baseOrd;
    for (int t = 0; t < iters; t++) {
        shuffle(ord.begin(), ord.end(), rng);
        runOrders(ord);
    }

    // Pair search among near-to-W elements
    {
        vector<pair<cpp_int, int>> near;
        near.reserve(n);
        for (int i = 0; i < n; i++) near.push_back({absDiff(a[i], W), i});
        sort(near.begin(), near.end(), [&](const auto& p1, const auto& p2) { return p1.first < p2.first; });

        int L = min(200, n);
        vector<int> idxs;
        idxs.reserve(L);
        for (int i = 0; i < L; i++) idxs.push_back(near[i].second);

        for (int ii = 0; ii < L; ii++) {
            for (int jj = ii + 1; jj < L; jj++) {
                int i = idxs[ii], j = idxs[jj];
                cpp_int s = a[i] + a[j];
                cpp_int d = absDiff(W, s);
                if (d < bestDiff) {
                    vector<unsigned char> sel(n, 0);
                    sel[i] = 1;
                    sel[j] = 1;
                    bestDiff = d;
                    bestSum = s;
                    bestSel.swap(sel);
                    if (bestDiff == 0) break;
                }
            }
            if (bestDiff == 0) break;
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (bestSel[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}