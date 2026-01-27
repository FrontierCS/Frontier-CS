#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n, m;
    if (!(cin >> n >> m)) return 0;

    // Trivial cases
    if (n == 0 || m == 0) {
        cout << 0 << "\n";
        return 0;
    }
    if (n == 1) {
        cout << m << "\n";
        for (int c = 1; c <= m; ++c) cout << 1 << " " << c << "\n";
        return 0;
    }
    if (m == 1) {
        cout << n << "\n";
        for (int r = 1; r <= n; ++r) cout << r << " " << 1 << "\n";
        return 0;
    }

    bool swapped = false;
    int R, C; // R = smaller dimension, C = larger dimension
    if (n <= m) {
        R = (int)n; C = (int)m; swapped = false;
    } else {
        R = (int)m; C = (int)n; swapped = true;
    }

    // Bitset parameters
    int W = (R + 63) >> 6;

    // Data structures
    vector<vector<uint64_t>> rowNei(R, vector<uint64_t>(W, 0));   // R x R bitset
    vector<vector<uint64_t>> colRows(C, vector<uint64_t>(W, 0));  // C x R bitset
    vector<int> colSize(C, 0);
    vector<int> rowDeg(R, 0);

    // Helper lambdas
    auto testBit = [&](const vector<uint64_t>& bs, int i)->bool {
        return (bs[i >> 6] >> (i & 63)) & 1ULL;
    };
    auto setBit = [&](vector<uint64_t>& bs, int i)->void {
        bs[i >> 6] |= (1ULL << (i & 63));
    };
    auto intersects = [&](const vector<uint64_t>& a, const vector<uint64_t>& b)->bool {
        for (int k = 0; k < W; ++k) if ((a[k] & b[k]) != 0ULL) return true;
        return false;
    };
    auto orAssign = [&](vector<uint64_t>& a, const vector<uint64_t>& b)->void {
        for (int k = 0; k < W; ++k) a[k] |= b[k];
    };
    auto iterateSetBits = [&](const vector<uint64_t>& bs, auto&& f)->void {
        for (int k = 0; k < W; ++k) {
            uint64_t x = bs[k];
            while (x) {
                uint64_t t = x & -x;
                int b = __builtin_ctzll(x);
                int idx = (k << 6) + b;
                f(idx);
                x -= t;
            }
        }
    };

    // Parameters for heuristic
    // rowDegCap ~ ceil(sqrt(C))
    int sroot = (int)floor(sqrt((long double)C));
    int rowDegCap = sroot * sroot == C ? sroot : sroot + 1;
    rowDegCap = max(1, min(C, rowDegCap));

    // Randomized tie-breakers (deterministic seed)
    uint64_t seed = (uint64_t)(n * 1000003LL + m * 911382323LL + 0x9e3779b97f4a7c15ULL);
    mt19937_64 rng(seed);
    vector<uint64_t> rowRand(R), colRand(C);
    for (int i = 0; i < R; ++i) rowRand[i] = rng();
    for (int j = 0; j < C; ++j) colRand[j] = rng();

    // Passes
    int maxPasses = rowDegCap + 2;
    vector<int> rowOrder(R), colOrder(C);
    iota(rowOrder.begin(), rowOrder.end(), 0);
    iota(colOrder.begin(), colOrder.end(), 0);

    for (int pass = 0; pass < maxPasses; ++pass) {
        bool anyAdded = false;

        // Sort rows by (deg, rand) ascending to balance rows
        sort(rowOrder.begin(), rowOrder.end(), [&](int a, int b){
            if (rowDeg[a] != rowDeg[b]) return rowDeg[a] < rowDeg[b];
            return rowRand[a] < rowRand[b];
        });

        // Sort columns by (size, rand) ascending to balance columns
        sort(colOrder.begin(), colOrder.end(), [&](int a, int b){
            if (colSize[a] != colSize[b]) return colSize[a] < colSize[b];
            return colRand[a] < colRand[b];
        });

        for (int jj = 0; jj < C; ++jj) {
            int j = colOrder[jj];
            if (colSize[j] == R) continue; // full

            // Try to add at most one row to this column in this pass
            bool addedInCol = false;
            for (int ii = 0; ii < R; ++ii) {
                int i = rowOrder[ii];
                if (rowDeg[i] >= rowDegCap) continue;
                if (testBit(colRows[j], i)) continue;
                if (intersects(rowNei[i], colRows[j])) continue;

                // Add (i, j)
                vector<uint64_t> S_before = colRows[j]; // copy small (W<=5)
                setBit(colRows[j], i);
                colSize[j]++;
                rowDeg[i]++;

                // rowNei[i] |= S_before
                orAssign(rowNei[i], S_before);
                // For each r2 in S_before, set bit i in rowNei[r2]
                int iw = i >> 6;
                uint64_t imask = 1ULL << (i & 63);
                for (int k = 0; k < W; ++k) {
                    uint64_t x = S_before[k];
                    while (x) {
                        uint64_t t = x & -x;
                        int b = __builtin_ctzll(x);
                        int r2 = (k << 6) + b;
                        rowNei[r2][iw] |= imask;
                        x -= t;
                    }
                }

                anyAdded = true;
                addedInCol = true;
                break;
            }
            (void)addedInCol;
        }

        if (!anyAdded) break;
    }

    // Collect results
    vector<pair<int,int>> ans;
    ans.reserve((size_t)n * (size_t)m);
    for (int j = 0; j < C; ++j) {
        for (int k = 0; k < W; ++k) {
            uint64_t x = colRows[j][k];
            while (x) {
                uint64_t t = x & -x;
                int b = __builtin_ctzll(x);
                int i = (k << 6) + b;
                if (i < R) {
                    if (!swapped) {
                        ans.emplace_back(i + 1, j + 1);
                    } else {
                        ans.emplace_back(j + 1, i + 1);
                    }
                }
                x -= t;
            }
        }
    }

    cout << ans.size() << "\n";
    for (auto &p : ans) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}