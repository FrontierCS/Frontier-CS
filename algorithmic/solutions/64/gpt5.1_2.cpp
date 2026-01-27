#include <bits/stdc++.h>
using namespace std;

mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());

unsigned long long random_mask(int bits) {
    if (bits <= 0) return 0ULL;
    unsigned long long mask = rng();
    if (bits < 64) {
        mask &= ((1ULL << bits) - 1ULL);
    }
    return mask;
}

inline long long llabs_ll(long long x) {
    return x >= 0 ? x : -x;
}

void local_search(vector<char>& sel, long long& sum, long long T, const vector<long long>& a, int max_passes = 50) {
    int n = (int)sel.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    long long curErr = llabs_ll(sum - T);

    for (int pass = 0; pass < max_passes; ++pass) {
        bool improved = false;
        shuffle(ord.begin(), ord.end(), rng);
        for (int k = 0; k < n; ++k) {
            int i = ord[k];
            long long newSum = sum + (sel[i] ? -a[i] : a[i]);
            long long newErr = llabs_ll(newSum - T);
            if (newErr < curErr) {
                sel[i] ^= 1;
                sum = newSum;
                curErr = newErr;
                improved = true;
            }
        }
        if (!improved) break;
    }
}

void exact_mitm(int n, long long T, const vector<long long>& a, vector<char>& bestSel) {
    int n1 = n / 2;
    int n2 = n - n1;

    int Lsize = 1 << n1;
    vector<long long> left_sums(Lsize);
    for (int mask = 1; mask < Lsize; ++mask) {
        int lsb = __builtin_ctz(mask);
        int prev = mask & (mask - 1);
        left_sums[mask] = left_sums[prev] + a[lsb];
    }

    int Rsize = 1 << n2;
    vector<long long> right_sums(Rsize);
    for (int mask = 1; mask < Rsize; ++mask) {
        int lsb = __builtin_ctz(mask);
        int prev = mask & (mask - 1);
        right_sums[mask] = right_sums[prev] + a[n1 + lsb];
    }

    struct RInfo { long long sum; int mask; };
    vector<RInfo> right(Rsize);
    for (int mask = 0; mask < Rsize; ++mask) {
        right[mask] = { right_sums[mask], mask };
    }
    sort(right.begin(), right.end(), [](const RInfo& x, const RInfo& y) {
        return x.sum < y.sum;
    });

    long long bestErr = llabs_ll(T);
    long long bestSum = 0;
    unsigned int bestLMask = 0, bestRMask = 0;

    for (unsigned int lmask = 0; lmask < (unsigned int)Lsize; ++lmask) {
        long long s1 = left_sums[lmask];
        long long target2 = T - s1;

        auto check_candidate = [&](const RInfo& cand) {
            long long total = s1 + cand.sum;
            long long err = llabs_ll(total - T);
            if (err < bestErr) {
                bestErr = err;
                bestSum = total;
                bestLMask = lmask;
                bestRMask = (unsigned int)cand.mask;
            }
        };

        auto it = lower_bound(right.begin(), right.end(), target2,
                              [](const RInfo& x, long long val) { return x.sum < val; });

        if (it != right.end()) {
            check_candidate(*it);
            auto it2 = it;
            int steps = 0;
            while (it2 != right.begin() && steps < 2) {
                --it2;
                check_candidate(*it2);
                ++steps;
            }
            auto it3 = it;
            steps = 0;
            while (it3 + 1 != right.end() && steps < 2) {
                ++it3;
                check_candidate(*it3);
                ++steps;
            }
        } else {
            check_candidate(right.back());
        }

        if (bestErr == 0) break;
    }

    bestSel.assign(n, 0);
    for (int i = 0; i < n1; ++i) {
        if (bestLMask & (1U << i)) bestSel[i] = 1;
    }
    for (int j = 0; j < n2; ++j) {
        if (bestRMask & (1U << j)) bestSel[n1 + j] = 1;
    }
    (void)bestSum; // bestSum not used further, but kept for clarity
}

void random_mitm(int n, long long T, const vector<long long>& a, int M,
                 vector<char>& outSel, long long& outSum) {
    int n1 = n / 2;
    int n2 = n - n1;

    struct SubInfo { long long sum; unsigned long long mask; };
    vector<SubInfo> right;
    right.reserve(M + 1);

    right.push_back({0, 0ULL}); // ensure empty subset

    for (int i = 0; i < M; ++i) {
        unsigned long long mask = random_mask(n2);
        long long sum = 0;
        for (int j = 0; j < n2; ++j) {
            if (mask & (1ULL << j)) sum += a[n1 + j];
        }
        right.push_back({sum, mask});
    }

    sort(right.begin(), right.end(), [](const SubInfo& x, const SubInfo& y) {
        return x.sum < y.sum;
    });

    long long bestErr = llabs_ll(T);
    long long bestSum = 0;
    unsigned long long bestLMask = 0, bestRMask = 0;

    auto search_right_and_consider = [&](unsigned long long lmask, long long s1) {
        long long target2 = T - s1;
        int lo = 0, hi = (int)right.size();
        while (lo < hi) {
            int mid = (lo + hi) >> 1;
            if (right[mid].sum < target2) lo = mid + 1;
            else hi = mid;
        }
        auto consider_idx = [&](int idx) {
            if (idx >= 0 && idx < (int)right.size()) {
                long long total = s1 + right[idx].sum;
                long long err = llabs_ll(total - T);
                if (err < bestErr) {
                    bestErr = err;
                    bestSum = total;
                    bestLMask = lmask;
                    bestRMask = right[idx].mask;
                }
            }
        };
        consider_idx(lo);
        consider_idx(lo - 1);
        consider_idx(lo + 1);
    };

    // left empty subset
    search_right_and_consider(0ULL, 0LL);

    for (int i = 0; i < M; ++i) {
        unsigned long long lmask = random_mask(n1);
        long long s1 = 0;
        for (int j = 0; j < n1; ++j) {
            if (lmask & (1ULL << j)) s1 += a[j];
        }
        search_right_and_consider(lmask, s1);
    }

    outSel.assign(n, 0);
    for (int i = 0; i < n1; ++i) {
        if (bestLMask & (1ULL << i)) outSel[i] = 1;
    }
    for (int j = 0; j < n2; ++j) {
        if (bestRMask & (1ULL << j)) outSel[n1 + j] = 1;
    }
    outSum = bestSum;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) {
        return 0;
    }
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    if (n <= 40) {
        vector<char> result;
        exact_mitm(n, T, a, result);
        for (int i = 0; i < n; ++i) cout << (result[i] ? '1' : '0');
        cout << '\n';
        return 0;
    }

    long long total = 0;
    for (int i = 0; i < n; ++i) total += a[i];

    vector<char> globalBestSel(n, 0);
    long long globalBestSum = 0;
    long long globalBestErr = llabs_ll(T - 0);

    auto update_global = [&](const vector<char>& sel, long long sum) {
        long long err = llabs_ll(sum - T);
        if (err < globalBestErr) {
            globalBestErr = err;
            globalBestSum = sum;
            globalBestSel = sel;
        }
    };

    // Candidate: all zeros + local search
    {
        vector<char> sel(n, 0);
        long long sum = 0;
        local_search(sel, sum, T, a);
        update_global(sel, sum);
    }

    // Candidate: all ones + local search
    {
        vector<char> sel(n, 1);
        long long sum = total;
        local_search(sel, sum, T, a);
        update_global(sel, sum);
    }

    // Candidate: greedy by descending a[i] + local search
    {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int i, int j) { return a[i] > a[j]; });
        vector<char> sel(n, 0);
        long long sum = 0;
        for (int id : idx) {
            long long newSum = sum + a[id];
            if (llabs_ll(newSum - T) <= llabs_ll(sum - T)) {
                sel[id] = 1;
                sum = newSum;
            }
        }
        local_search(sel, sum, T, a);
        update_global(sel, sum);
    }

    // Candidate: random meet-in-the-middle + local search
    {
        vector<char> sel;
        long long sum = 0;
        int M = 100000;
        random_mitm(n, T, a, M, sel, sum);
        local_search(sel, sum, T, a);
        update_global(sel, sum);
    }

    for (int i = 0; i < n; ++i) cout << (globalBestSel[i] ? '1' : '0');
    cout << '\n';

    (void)globalBestSum; // not used further, but kept for completeness
    return 0;
}