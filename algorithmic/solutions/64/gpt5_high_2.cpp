#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

static inline int64 llabs64(int64 x){ return x >= 0 ? x : -x; }

vector<int64> generateSums(const vector<int64>& w) {
    int k = (int)w.size();
    int N = 1 << k;
    vector<int64> sums(N);
    sums[0] = 0;
    for (int i = 0; i < k; ++i) {
        int curSize = 1 << i;
        for (int m = 0; m < curSize; ++m) {
            sums[m + curSize] = sums[m] + w[i];
        }
    }
    return sums;
}

int findMaskBySum(const vector<int64>& sums, int64 target) {
    for (int i = 0, n = (int)sums.size(); i < n; ++i) {
        if (sums[i] == target) return i;
    }
    return 0;
}

int64 computeSum(const vector<unsigned char>& x, const vector<int64>& a) {
    int n = (int)a.size();
    __int128 acc = 0;
    for (int i = 0; i < n; ++i) if (x[i]) acc += a[i];
    if (acc > LLONG_MAX) return LLONG_MAX;
    if (acc < LLONG_MIN) return LLONG_MIN;
    return (int64)acc;
}

void refineSolution(vector<unsigned char>& x, const vector<int64>& a, int64 T) {
    int n = (int)a.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        return a[i] > a[j];
    });

    int64 S = computeSum(x, a);
    int64 bestErr = llabs64(S - T);

    bool improved = true;
    while (improved) {
        improved = false;

        // Single flips
        for (int idx : order) {
            int64 d = x[idx] ? -a[idx] : +a[idx];
            int64 newErr = llabs64(S + d - T);
            if (newErr < bestErr) {
                x[idx] ^= 1;
                S += d;
                bestErr = newErr;
                improved = true;
            }
        }

        // Pair flips (first improving move)
        bool pairImproved = false;
        for (int i = 0; i < n && !pairImproved; ++i) {
            int64 d1 = x[i] ? -a[i] : +a[i];
            for (int j = i + 1; j < n; ++j) {
                int64 d2 = x[j] ? -a[j] : +a[j];
                int64 newErr = llabs64(S + d1 + d2 - T);
                if (newErr < bestErr) {
                    x[i] ^= 1;
                    x[j] ^= 1;
                    S += d1 + d2;
                    bestErr = newErr;
                    pairImproved = true;
                    break;
                }
            }
        }
        if (pairImproved) improved = true;
    }
}

vector<unsigned char> greedyFromZero(const vector<int>& order, const vector<int64>& a, int64 T) {
    int n = (int)a.size();
    vector<unsigned char> x(n, 0);
    int64 S = 0;
    for (int idx : order) {
        int64 newErr = llabs64(S + a[idx] - T);
        int64 curErr = llabs64(S - T);
        if (newErr < curErr) {
            x[idx] = 1;
            S += a[idx];
        }
    }
    return x;
}

vector<unsigned char> greedyFromFull(const vector<int>& order, const vector<int64>& a, int64 T) {
    int n = (int)a.size();
    vector<unsigned char> x(n, 1);
    int64 S = 0;
    for (int i = 0; i < n; ++i) S += a[i];
    for (int idx : order) {
        int64 newErr = llabs64(S - a[idx] - T);
        int64 curErr = llabs64(S - T);
        if (newErr < curErr) {
            x[idx] = 0;
            S -= a[idx];
        }
    }
    return x;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if (!(cin >> n >> T)) {
        return 0;
    }
    vector<int64> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    // Prepare index order by value descending
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    // Decide K for meet-in-the-middle with cap on subset count per half
    const int SUB_LIMIT = 1 << 20; // up to about 1,048,576 per half
    int maxHalf = 0;
    while ((1 << (maxHalf + 1)) <= SUB_LIMIT) maxHalf++;
    int K = min(n, 2 * maxHalf); // typically 40

    vector<unsigned char> bestSol(n, 0);
    int64 bestErr = llabs64(0 - T);

    auto consider = [&](vector<unsigned char>& sol){
        refineSolution(sol, a, T);
        int64 S = computeSum(sol, a);
        int64 err = llabs64(S - T);
        if (err < bestErr) {
            bestErr = err;
            bestSol = sol;
        }
    };

    // 1) Meet-in-the-middle on top K items
    if (K > 0) {
        int kL = K / 2, kR = K - kL;
        vector<int64> wL(kL), wR(kR);
        for (int i = 0; i < kL; ++i) wL[i] = a[idx[i]];
        for (int i = 0; i < kR; ++i) wR[i] = a[idx[kL + i]];
        vector<int64> sumsL = generateSums(wL);
        vector<int64> sumsR = generateSums(wR);
        vector<int64> sumsRsorted = sumsR;
        sort(sumsRsorted.begin(), sumsRsorted.end());

        int64 bestLocalErr = (int64)LLONG_MAX;
        int bestLmask = 0;
        int64 bestRsum = 0;

        for (int lmask = 0, NL = (int)sumsL.size(); lmask < NL; ++lmask) {
            int64 lsum = sumsL[lmask];
            int64 targetR = T - lsum;
            auto it = lower_bound(sumsRsorted.begin(), sumsRsorted.end(), targetR);
            if (it != sumsRsorted.end()) {
                int64 cand = *it;
                int64 err = llabs64(lsum + cand - T);
                if (err < bestLocalErr) {
                    bestLocalErr = err;
                    bestLmask = lmask;
                    bestRsum = cand;
                }
            }
            if (it != sumsRsorted.begin()) {
                --it;
                int64 cand = *it;
                int64 err = llabs64(lsum + cand - T);
                if (err < bestLocalErr) {
                    bestLocalErr = err;
                    bestLmask = lmask;
                    bestRsum = cand;
                }
            }
        }

        int bestRmask = findMaskBySum(sumsR, bestRsum);

        vector<unsigned char> sol(n, 0);
        for (int i = 0; i < kL; ++i) {
            if (bestLmask & (1 << i)) sol[idx[i]] = 1;
        }
        for (int i = 0; i < kR; ++i) {
            if (bestRmask & (1 << i)) sol[idx[kL + i]] = 1;
        }
        consider(sol);
    }

    // 2) Greedy from zero in descending order
    {
        vector<unsigned char> sol = greedyFromZero(idx, a, T);
        consider(sol);
    }

    // 3) Greedy from full in descending order
    {
        vector<unsigned char> sol = greedyFromFull(idx, a, T);
        consider(sol);
    }

    // Print best solution as binary string
    string out;
    out.reserve(n);
    for (int i = 0; i < n; ++i) out.push_back(bestSol[i] ? '1' : '0');
    cout << out << '\n';

    return 0;
}