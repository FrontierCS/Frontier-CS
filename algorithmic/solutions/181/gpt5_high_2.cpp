#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getcharFast() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c = getcharFast();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getcharFast();
            if (!c) return false;
        }
        int sign = 1;
        if (c == '-') { sign = -1; c = getcharFast(); }
        long long val = 0;
        for (; c >= '0' && c <= '9'; c = getcharFast())
            val = val * 10 + (c - '0');
        out = (T)(val * sign);
        return true;
    }
};

static inline long long compute_cost(const vector<int>& p, const vector<vector<int>>& outF, const vector<uint8_t>& D, int n) {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        int rowBase = pi * n;
        const auto &row = outF[i];
        for (int j : row) {
            cost += D[rowBase + p[j]];
        }
    }
    return cost;
}

static inline long long delta_swap(int a, int b, const vector<int>& p,
                                   const vector<vector<int>>& outF,
                                   const vector<vector<int>>& inF,
                                   const vector<uint8_t>& D, int n) {
    if (a == b) return 0;
    int A = p[a], B = p[b];
    if (A == B) return 0;

    long long delta = 0;
    int rowA = A * n, rowB = B * n;

    bool has_aa = false, has_ab = false, has_ba = false, has_bb = false;

    // Outgoing from a
    const auto &oa = outF[a];
    for (int j : oa) {
        if (j == a) { has_aa = true; continue; }
        if (j == b) { has_ab = true; continue; }
        delta += (int)D[rowB + p[j]] - (int)D[rowA + p[j]];
    }
    // Outgoing from b
    const auto &ob = outF[b];
    for (int j : ob) {
        if (j == b) { has_bb = true; continue; }
        if (j == a) { has_ba = true; continue; }
        delta += (int)D[rowA + p[j]] - (int)D[rowB + p[j]];
    }

    // Incoming to a (i != a,b)
    const auto &ia = inF[a];
    for (int i : ia) {
        if (i == a || i == b) continue;
        int pi = p[i];
        delta += (int)D[pi * n + B] - (int)D[pi * n + A];
    }
    // Incoming to b (i != a,b)
    const auto &ib = inF[b];
    for (int i : ib) {
        if (i == a || i == b) continue;
        int pi = p[i];
        delta += (int)D[pi * n + A] - (int)D[pi * n + B];
    }

    // Special pairs
    if (has_aa) delta += (int)D[rowB + B] - (int)D[rowA + A];
    if (has_bb) delta += (int)D[rowA + A] - (int)D[rowB + B];
    if (has_ab) delta += (int)D[rowB + A] - (int)D[rowA + B];
    if (has_ba) delta += (int)D[rowA + B] - (int)D[rowB + A];

    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) return 0;

    vector<uint8_t> D((size_t)n * n);
    vector<int> outD(n, 0), inD(n, 0);

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; fs.nextInt(x);
            D[(size_t)i * n + j] = (uint8_t)x;
            if (x) { outD[i]++; inD[j]++; }
        }
    }

    vector<vector<int>> outF(n), inF(n);
    vector<int> outFdeg(n, 0), inFdeg(n, 0);
    long long totalFlow = 0;

    // Read F and build adjacency
    for (int i = 0; i < n; ++i) {
        outF[i].reserve(n / 4 + 1); // heuristic reserve
        for (int j = 0; j < n; ++j) {
            int x; fs.nextInt(x);
            if (x) {
                outF[i].push_back(j);
                outFdeg[i]++;
                inF[j].push_back(i);
                inFdeg[j]++;
                totalFlow++;
            }
        }
    }

    // Degree arrays
    vector<int> degF(n), degD(n);
    for (int i = 0; i < n; ++i) {
        degF[i] = outFdeg[i] + inFdeg[i];
        degD[i] = outD[i] + inD[i];
    }

    // Initial mapping: sort facilities by high degF -> locations by low degD
    vector<int> idsF(n), idsD(n);
    iota(idsF.begin(), idsF.end(), 0);
    iota(idsD.begin(), idsD.end(), 0);
    sort(idsF.begin(), idsF.end(), [&](int a, int b) {
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        if (outFdeg[a] != outFdeg[b]) return outFdeg[a] > outFdeg[b];
        return a < b;
    });
    sort(idsD.begin(), idsD.end(), [&](int a, int b) {
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        if (outD[a] != outD[b]) return outD[a] < outD[b];
        return a < b;
    });

    vector<int> p(n, -1);
    for (int t = 0; t < n; ++t) {
        p[idsF[t]] = idsD[t];
    }

    long long cost = compute_cost(p, outF, D, n);

    // Prepare helper lists for local search
    vector<int> facilities_by_deg = idsF; // already high to low
    int topSize = max(1, n / 3);
    int bottomSize = max(1, n / 3);
    vector<int> topF(facilities_by_deg.begin(), facilities_by_deg.begin() + topSize);
    vector<int> botF(facilities_by_deg.end() - bottomSize, facilities_by_deg.end());

    // Random engine
    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto try_improve_pair = [&](int a, int b) -> bool {
        if (a == b) return false;
        long long d = delta_swap(a, b, p, outF, inF, D, n);
        if (d < 0) {
            swap(p[a], p[b]);
            cost += d;
            return true;
        }
        return false;
    };

    // Targeted pass: for each high-degree facility, try a few candidates from low-degree set
    int K = 6; // candidates per facility
    for (int round = 0; round < 1; ++round) { // single pass to stay within time
        bool improved = false;
        for (int idx = 0; idx < n; ++idx) {
            int a = facilities_by_deg[idx];
            long long bestDelta = 0;
            int bestB = -1;
            for (int t = 0; t < K; ++t) {
                int b = botF[(size_t)(rng() % botF.size())];
                if (b == a) continue;
                long long d = delta_swap(a, b, p, outF, inF, D, n);
                if (d < bestDelta) {
                    bestDelta = d;
                    bestB = b;
                }
            }
            if (bestB != -1) {
                swap(p[a], p[bestB]);
                cost += bestDelta;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Random hill-climbing limited attempts
    int maxAttempts = min(10000, n * 5);
    int noImprove = 0;
    for (int attempt = 0; attempt < maxAttempts && noImprove < n * 2; ++attempt) {
        int a, b;
        if ((rng() % 100) < 70 && n > 1) {
            a = topF[(size_t)(rng() % topF.size())];
            b = botF[(size_t)(rng() % botF.size())];
            if (a == b) {
                a = (int)(rng() % n);
                do { b = (int)(rng() % n); } while (b == a);
            }
        } else {
            a = (int)(rng() % n);
            do { b = (int)(rng() % n); } while (b == a);
        }
        bool ok = try_improve_pair(a, b);
        if (ok) noImprove = 0;
        else noImprove++;
    }

    // Output permutation 1-indexed
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}