#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

struct Attempt {
    vector<char> sel;
    cpp_int sum;
    cpp_int diff;
};

void localImprove(vector<char>& sel, cpp_int& S, const vector<cpp_int>& a, const cpp_int& W, int stepsLimit) {
    int n = (int)a.size();
    for (int step = 0; step < stepsLimit; ++step) {
        cpp_int curDiff = absDiff(W, S);
        bool improved = false;
        if (S > W) {
            int bestK = -1;
            cpp_int bestDiff = curDiff;
            cpp_int bestNewS = S;
            for (int i = 0; i < n; ++i) {
                if (sel[i]) {
                    cpp_int newS = S - a[i];
                    cpp_int d = absDiff(W, newS);
                    if (d < bestDiff) {
                        bestDiff = d;
                        bestK = i;
                        bestNewS = newS;
                    }
                }
            }
            if (bestK != -1) {
                sel[bestK] = 0;
                S = bestNewS;
                improved = true;
            }
        } else {
            int bestJ = -1;
            cpp_int bestDiff = curDiff;
            cpp_int bestNewS = S;
            for (int i = 0; i < n; ++i) {
                if (!sel[i]) {
                    if (a[i] == 0) continue;
                    cpp_int newS = S + a[i];
                    cpp_int d = absDiff(W, newS);
                    if (d < bestDiff) {
                        bestDiff = d;
                        bestJ = i;
                        bestNewS = newS;
                    }
                }
            }
            if (bestJ != -1) {
                sel[bestJ] = 1;
                S = bestNewS;
                improved = true;
            }
        }
        if (!improved) break;
    }
}

Attempt greedyOrder(const vector<int>& ord, const vector<cpp_int>& a, const cpp_int& W) {
    int n = (int)a.size();
    vector<char> sel(n, 0);
    cpp_int S = 0;
    cpp_int curDiff = absDiff(W, S);

    for (int idx : ord) {
        if (a[idx] == 0) continue;
        cpp_int newS = S + a[idx];
        cpp_int newDiff = absDiff(W, newS);
        if (newDiff < curDiff) {
            sel[idx] = 1;
            S = newS;
            curDiff = newDiff;
            if (S > W) break;
        }
    }

    // Small local improvement
    localImprove(sel, S, a, W, 3);
    curDiff = absDiff(W, S);

    return {sel, S, curDiff};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cpp_int W;
    if (!(cin >> n >> W)) {
        return 0;
    }
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    // Initial best: empty selection
    vector<char> bestSel(n, 0);
    cpp_int bestSum = 0;
    cpp_int bestDiff = absDiff(W, bestSum);

    // Best single item
    int bestIdx = -1;
    cpp_int bestSingleDiff = bestDiff;
    for (int i = 0; i < n; ++i) {
        cpp_int d = absDiff(W, a[i]);
        if (d < bestSingleDiff) {
            bestSingleDiff = d;
            bestIdx = i;
        }
    }
    if (bestIdx != -1) {
        vector<char> sel(n, 0);
        sel[bestIdx] = 1;
        bestSel = sel;
        bestSum = a[bestIdx];
        bestDiff = bestSingleDiff;
    }

    // Orders
    vector<int> ordAsc(n), ordDesc(n);
    iota(ordAsc.begin(), ordAsc.end(), 0);
    iota(ordDesc.begin(), ordDesc.end(), 0);

    sort(ordAsc.begin(), ordAsc.end(), [&](int i, int j){
        if (a[i] == a[j]) return i < j;
        return a[i] < a[j];
    });
    sort(ordDesc.begin(), ordDesc.end(), [&](int i, int j){
        if (a[i] == a[j]) return i < j;
        return a[i] > a[j];
    });

    // Greedy descending
    {
        Attempt res = greedyOrder(ordDesc, a, W);
        if (res.diff < bestDiff) {
            bestDiff = res.diff;
            bestSel = move(res.sel);
            bestSum = move(res.sum);
        }
    }

    // Greedy ascending
    {
        Attempt res = greedyOrder(ordAsc, a, W);
        if (res.diff < bestDiff) {
            bestDiff = res.diff;
            bestSel = move(res.sel);
            bestSum = move(res.sum);
        }
    }

    // A couple of random shuffles to diversify
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    vector<int> ordRand = ordDesc;
    for (int attempt = 0; attempt < 3; ++attempt) {
        shuffle(ordRand.begin(), ordRand.end(), rng);
        Attempt res = greedyOrder(ordRand, a, W);
        if (res.diff < bestDiff) {
            bestDiff = res.diff;
            bestSel = move(res.sel);
            bestSum = move(res.sum);
        }
    }

    // Final local improvement from current best
    {
        vector<char> sel = bestSel;
        cpp_int S = bestSum;
        localImprove(sel, S, a, W, 5);
        cpp_int d = absDiff(W, S);
        if (d < bestDiff) {
            bestDiff = d;
            bestSel = move(sel);
            bestSum = move(S);
        }
    }

    // Output
    for (int i = 0; i < n; ++i) {
        cout << (bestSel[i] ? 1 : 0) << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}