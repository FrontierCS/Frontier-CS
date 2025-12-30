#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct PairHash {
    size_t operator()(const long long &x) const {
        return std::hash<long long>{}(x);
    }
};

int n;
long long k;
long long usedQueries = 0;

unordered_map<long long, long long, PairHash> cache;

inline long long keyPair(int i, int j) {
    return ((long long)i << 21) ^ (long long)j;
}

long long ask(int i, int j) {
    long long key = keyPair(i, j);
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    cout << "QUERY " << i << " " << j << "\n";
    cout.flush();
    long long v;
    if (!(cin >> v)) {
        // If interactor fails, exit
        exit(0);
    }
    usedQueries++;
    cache[key] = v;
    return v;
}

struct CountRes {
    long long cnt;
    vector<int> cutoff; // j(mid) per row, number of elements <= mid in each row
};

CountRes countLeq(long long mid, const vector<int> &jLo, const vector<int> &jHi) {
    CountRes res;
    res.cnt = 0;
    res.cutoff.assign(n + 1, 0);
    int j = jHi[1];
    if (j < 0) j = 0;
    if (j > n) j = n;
    for (int i = 1; i <= n; i++) {
        int L = jLo[i];
        int R = jHi[i];
        if (R < 0) R = 0;
        if (R > n) R = n;
        if (L < 0) L = 0;
        if (L > n) L = n;
        if (R <= L) {
            res.cutoff[i] = L;
            res.cnt += L;
            continue;
        }
        if (j > R) j = R;
        while (j > L) {
            long long v = ask(i, j);
            if (v <= mid) {
                res.cutoff[i] = j;
                res.cnt += j;
                break;
            } else {
                j--;
            }
        }
        if (j <= L) {
            res.cutoff[i] = L;
            res.cnt += L;
        }
        // j is already <= current j for next row, ensure it does not exceed next R in next iteration handled at loop start
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    // Budgets
    long long NLL = 1LL * n * n;

    // Choose counts budget conservatively
    int countsBudget = (int)min(30LL, (45000LL) / max(1, 2 * n)); // aim to keep room for sampling + enumeration
    if (countsBudget < 1) countsBudget = 1;

    int reserved = 100; // reserve for safety and final DONE
    long long left = 50000 - countsBudget * (2LL * n) - reserved;
    if (left < 0) left = 0;

    // Enumeration budget E and sample size S
    int E = (int)min(5000LL, max(400LL, left / 3)); // between 400 and 5000
    long long SBudget = left - E;
    if (SBudget < 0) SBudget = 0;
    long long SNeed = max(1LL, (NLL + E - 1) / E);
    long long Ssize = min(SBudget, max(100LL, min(6000LL, SNeed * 2))); // try to take up to 2*SNeed but cap at 6000
    if (Ssize > (long long)n * n) Ssize = (long long)n * n;

    // Sample values
    vector<long long> sampleVals;
    sampleVals.reserve((size_t)Ssize);

    // Create sample positions: a grid plus random fill
    unordered_set<long long, PairHash> seen;
    seen.reserve((size_t)Ssize * 2 + 10);
    uint64_t seed = 1469598103934665603ULL ^ (uint64_t)n * 1181783497276652981ULL ^ ((uint64_t)k << 1);
    auto rng = [&]() -> uint64_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        seed ^= seed << 8;
        return seed;
    };
    auto randInt = [&](int low, int high)->int {
        return low + (int)(rng() % (uint64_t)(high - low + 1));
    };

    vector<pair<int,int>> samplePos;
    samplePos.reserve((size_t)Ssize);

    if (Ssize > 0) {
        int g = (int)floor(sqrt((long double)Ssize));
        if (g > 0) {
            vector<int> rows; rows.reserve(g);
            vector<int> cols; cols.reserve(g);
            for (int i = 1; i <= g; i++) {
                int r = (int)((i * (long long)n) / (g + 1));
                if (r < 1) r = 1;
                if (r > n) r = n;
                rows.push_back(r);
            }
            for (int j = 1; j <= g; j++) {
                int c = (int)((j * (long long)n) / (g + 1));
                if (c < 1) c = 1;
                if (c > n) c = n;
                cols.push_back(c);
            }
            for (int rr : rows) {
                for (int cc : cols) {
                    long long key = keyPair(rr, cc);
                    if (seen.insert(key).second) {
                        samplePos.emplace_back(rr, cc);
                    }
                    if ((long long)samplePos.size() >= Ssize) break;
                }
                if ((long long)samplePos.size() >= Ssize) break;
            }
        }
        // Add random fill until reaching Ssize
        while ((long long)samplePos.size() < Ssize) {
            int i = randInt(1, n);
            int j = randInt(1, n);
            long long key = keyPair(i, j);
            if (seen.insert(key).second) samplePos.emplace_back(i, j);
        }

        for (auto &p : samplePos) {
            long long v = ask(p.first, p.second);
            sampleVals.push_back(v);
        }
        sort(sampleVals.begin(), sampleVals.end());
        sampleVals.erase(unique(sampleVals.begin(), sampleVals.end()), sampleVals.end());
    }

    if (sampleVals.empty()) {
        // Fallback: directly do countsBudget binary searches on numeric range using extremes
        // Query min and max
        long long minVal = ask(1,1);
        long long maxVal = ask(n,n);
        if (minVal > maxVal) swap(minVal, maxVal);

        vector<int> jLo(n + 1, 0), jHi(n + 1, n);
        long long cLo = 0, cHi = NLL;

        int usedCounts = 0;
        while (usedCounts < countsBudget && cHi - cLo > E) {
            long long mid = minVal + (( (__int128)maxVal - minVal) >> 1);
            if (mid == minVal && mid + 1 <= maxVal) mid++;
            auto res = countLeq(mid, jLo, jHi);
            usedCounts++;
            if (res.cnt >= k) {
                jHi.swap(res.cutoff);
                cHi = res.cnt;
                maxVal = mid;
            } else {
                jLo.swap(res.cutoff);
                cLo = res.cnt;
                minVal = mid;
            }
        }

        long long W = cHi - cLo;
        vector<long long> cand; cand.reserve((size_t)W);
        for (int i = 1; i <= n; i++) {
            for (int j = jLo[i] + 1; j <= jHi[i]; j++) {
                cand.push_back(ask(i, j));
            }
        }
        long long rank = k - cLo;
        if (rank <= 0) {
            cout << "DONE " << minVal << "\n";
            cout.flush();
            return 0;
        }
        if (rank > (long long)cand.size()) {
            cout << "DONE " << maxVal << "\n";
            cout.flush();
            return 0;
        }
        nth_element(cand.begin(), cand.begin() + (rank - 1), cand.end());
        cout << "DONE " << cand[rank - 1] << "\n";
        cout.flush();
        return 0;
    }

    // Initialize boundaries
    vector<int> jLo(n + 1, 0), jHi(n + 1, n);
    long long cLo = 0, cHi = NLL;

    int li = -1;
    int hiIndex = (int)sampleVals.size();
    int usedCounts = 0;

    // Main phase: binary search over sample values
    while (usedCounts < countsBudget && hiIndex - li > 1) {
        int midIndex = li + (hiIndex - li) / 2;
        long long pivot = sampleVals[midIndex];
        auto res = countLeq(pivot, jLo, jHi);
        usedCounts++;
        if (res.cnt >= k) {
            hiIndex = midIndex;
            jHi.swap(res.cutoff);
            cHi = res.cnt;
        } else {
            li = midIndex;
            jLo.swap(res.cutoff);
            cLo = res.cnt;
        }
    }

    long long loValNum = (li >= 0 ? sampleVals[li] : sampleVals.front());
    long long hiValNum = (hiIndex < (int)sampleVals.size() ? sampleVals[hiIndex] : sampleVals.back());

    // If still too large, additional numeric pivots between current bracket
    while (usedCounts < countsBudget && (cHi - cLo) > E) {
        long long a = loValNum, b = hiValNum;
        if (a >= b) break;
        long long mid = a + (((__int128)b - a) >> 1);
        if (mid == a) mid++;
        if (mid == b) mid--;
        if (mid <= a || mid >= b) break;
        auto res = countLeq(mid, jLo, jHi);
        usedCounts++;
        if (res.cnt >= k) {
            jHi.swap(res.cutoff);
            cHi = res.cnt;
            hiValNum = mid;
        } else {
            jLo.swap(res.cutoff);
            cLo = res.cnt;
            loValNum = mid;
        }
    }

    // Final enumeration
    long long W = cHi - cLo;
    vector<long long> cand; cand.reserve((size_t)W);
    for (int i = 1; i <= n; i++) {
        for (int j = jLo[i] + 1; j <= jHi[i]; j++) {
            cand.push_back(ask(i, j));
        }
    }

    long long rank = k - cLo;
    if (rank <= 0) {
        cout << "DONE " << loValNum << "\n";
        cout.flush();
        return 0;
    }
    if (rank > (long long)cand.size()) {
        cout << "DONE " << hiValNum << "\n";
        cout.flush();
        return 0;
    }

    nth_element(cand.begin(), cand.begin() + (rank - 1), cand.end());
    long long ans = cand[rank - 1];
    cout << "DONE " << ans << "\n";
    cout.flush();
    return 0;
}