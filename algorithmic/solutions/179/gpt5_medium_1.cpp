#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>
using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parseBig(const string& s) {
    cpp_int v = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            v *= 10;
            v += (c - '0');
        }
    }
    return v;
}

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string sW;
    if (!(cin >> n >> sW)) {
        return 0;
    }
    cpp_int W = parseBig(sW);

    vector<cpp_int> a(n);
    cpp_int M = 0;
    for (int i = 0; i < n; ++i) {
        string s; cin >> s;
        a[i] = parseBig(s);
        if (a[i] > M) M = a[i];
    }

    // Precompute indices sorted by descending and ascending values
    vector<int> iddesc(n), idasc(n);
    iota(iddesc.begin(), iddesc.end(), 0);
    iota(idasc.begin(), idasc.end(), 0);
    sort(iddesc.begin(), iddesc.end(), [&](int i, int j){ return a[i] > a[j]; });
    sort(idasc.begin(), idasc.end(), [&](int i, int j){ return a[i] < a[j]; });

    vector<uint8_t> bestPick(n, 0);
    cpp_int bestDiff = W + M + 1; // larger than possible max diff
    cpp_int bestSum = 0;

    auto consider = [&](const vector<uint8_t>& pick, const cpp_int& sum) {
        cpp_int d = absDiff(sum, W);
        if (d < bestDiff) {
            bestDiff = d;
            bestPick = pick;
            bestSum = sum;
        }
    };

    // Candidate 1: all zeros
    {
        vector<uint8_t> pick(n, 0);
        cpp_int sum = 0;
        consider(pick, sum);
    }

    // Candidate 2: single best item
    {
        int bestIdx = -1;
        cpp_int bestD = bestDiff;
        for (int i = 0; i < n; ++i) {
            cpp_int d = absDiff(a[i], W);
            if (d < bestD) {
                bestD = d;
                bestIdx = i;
            }
        }
        if (bestIdx != -1) {
            vector<uint8_t> pick(n, 0);
            pick[bestIdx] = 1;
            consider(pick, a[bestIdx]);
        }
    }

    auto try_improve = [&](const vector<uint8_t>& basePick, const cpp_int& baseSum) {
        // Add one item
        {
            int bestIdx = -1;
            cpp_int bestD = absDiff(baseSum, W);
            for (int i = 0; i < n; ++i) if (!basePick[i]) {
                cpp_int s2 = baseSum + a[i];
                cpp_int d2 = absDiff(s2, W);
                if (d2 < bestD) {
                    bestD = d2;
                    bestIdx = i;
                }
            }
            if (bestIdx != -1) {
                vector<uint8_t> pick = basePick;
                pick[bestIdx] = 1;
                consider(pick, baseSum + a[bestIdx]);
            }
        }
        // Remove one item
        {
            int bestIdx = -1;
            cpp_int bestD = absDiff(baseSum, W);
            for (int i = 0; i < n; ++i) if (basePick[i]) {
                cpp_int s2 = baseSum - a[i];
                cpp_int d2 = absDiff(s2, W);
                if (d2 < bestD) {
                    bestD = d2;
                    bestIdx = i;
                }
            }
            if (bestIdx != -1) {
                vector<uint8_t> pick = basePick;
                pick[bestIdx] = 0;
                consider(pick, baseSum - a[bestIdx]);
            }
        }
        // Swap one chosen with one unchosen (limited top L by value)
        {
            const int L = 100;
            vector<int> chosenTop;
            vector<int> unchosenTop;
            chosenTop.reserve(min(L, n));
            unchosenTop.reserve(min(L, n));
            for (int idx : iddesc) {
                if ((int)chosenTop.size() < L && basePick[idx]) chosenTop.push_back(idx);
                if ((int)unchosenTop.size() < L && !basePick[idx]) unchosenTop.push_back(idx);
                if ((int)chosenTop.size() >= L && (int)unchosenTop.size() >= L) break;
            }
            int bi = -1, bj = -1;
            cpp_int bestD = absDiff(baseSum, W);
            for (int i : chosenTop) {
                for (int j : unchosenTop) {
                    cpp_int s2 = baseSum - a[i] + a[j];
                    cpp_int d2 = absDiff(s2, W);
                    if (d2 < bestD) {
                        bestD = d2;
                        bi = i; bj = j;
                    }
                }
            }
            if (bi != -1) {
                vector<uint8_t> pick = basePick;
                pick[bi] = 0;
                pick[bj] = 1;
                consider(pick, baseSum - a[bi] + a[bj]);
            }
        }
    };

    // Candidate 3: Descending greedy without exceeding W
    {
        vector<uint8_t> pick(n, 0);
        cpp_int sum = 0;
        for (int idx : iddesc) {
            if (sum + a[idx] <= W) {
                pick[idx] = 1;
                sum += a[idx];
            }
        }
        consider(pick, sum);
        try_improve(pick, sum);
    }

    // Candidate 4: Ascending greedy around W (include or exclude the next overshoot)
    {
        vector<uint8_t> pick(n, 0);
        cpp_int sum = 0;
        int k = 0;
        for (; k < n; ++k) {
            int idx = idasc[k];
            if (sum + a[idx] <= W) {
                pick[idx] = 1;
                sum += a[idx];
            } else {
                break;
            }
        }
        consider(pick, sum);
        if (k < n) {
            vector<uint8_t> pick2 = pick;
            pick2[idasc[k]] = 1;
            cpp_int sum2 = sum + a[idasc[k]];
            consider(pick2, sum2);
            try_improve(pick2, sum2);
        }
        try_improve(pick, sum);
    }

    // Output best pick
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << int(bestPick[i]);
    }
    cout << '\n';
    return 0;
}