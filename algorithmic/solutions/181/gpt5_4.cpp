#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline bool skip() {
        char c;
        do {
            c = getch();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }
    inline int nextInt() {
        if (!skip()) return 0;
        int x = 0, sgn = 1;
        char c = getch();
        if (c == '-') { sgn = -1; c = getch(); }
        for (; c > ' '; c = getch()) x = x * 10 + (c - '0');
        return x * sgn;
    }
};

static inline int getBit(const vector<uint64_t>& row, int j) {
    return (int)((row[(unsigned)j >> 6] >> (j & 63)) & 1ULL);
}
static inline void setBit(vector<uint64_t>& row, int j) {
    row[(unsigned)j >> 6] |= (1ULL << (j & 63));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;

    int n = fs.nextInt();
    int W = (n + 63) >> 6;

    vector<vector<uint64_t>> Drow(n, vector<uint64_t>(W, 0));
    vector<vector<uint64_t>> Frow(n, vector<uint64_t>(W, 0));

    vector<int> degDRow(n, 0), degDCol(n, 0);
    vector<int> degFRow(n, 0), degFCol(n, 0);

    // Read D
    for (int i = 0; i < n; ++i) {
        int rowSum = 0;
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            if (x) {
                setBit(Drow[i], j);
                rowSum++;
                degDCol[j]++;
            }
        }
        degDRow[i] = rowSum;
    }

    // Read F
    for (int i = 0; i < n; ++i) {
        int rowSum = 0;
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            if (x) {
                setBit(Frow[i], j);
                rowSum++;
                degFCol[j]++;
            }
        }
        degFRow[i] = rowSum;
    }

    vector<int> degD(n), degF(n);
    for (int i = 0; i < n; ++i) {
        degD[i] = degDRow[i] + degDCol[i];
        degF[i] = degFRow[i] + degFCol[i];
    }

    vector<int> fac(n), loc(n);
    iota(fac.begin(), fac.end(), 0);
    iota(loc.begin(), loc.end(), 0);

    // Sort facilities by descending degF
    sort(fac.begin(), fac.end(), [&](int a, int b){
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        if (degFRow[a] != degFRow[b]) return degFRow[a] > degFRow[b];
        return a < b;
    });
    // Sort locations by ascending degD
    sort(loc.begin(), loc.end(), [&](int a, int b){
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        if (degDRow[a] != degDRow[b]) return degDRow[a] < degDRow[b];
        return a < b;
    });

    vector<int> p(n, -1), inv(n, -1);
    for (int k = 0; k < n; ++k) {
        int i = fac[k];
        int l = loc[k];
        p[i] = l;
        inv[l] = i;
    }

    // Local search: random pairwise swaps with O(n) delta using inclusion-exclusion
    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT_SEC = 0.8; // conservative time budget
    const int MAX_TRIALS = 12000;

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto time_elapsed = [&]() {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    auto getD = [&](int r, int c)->int {
        return getBit(Drow[r], c);
    };
    auto getF = [&](int r, int c)->int {
        return getBit(Frow[r], c);
    };

    int trials = 0;
    while (trials < MAX_TRIALS && time_elapsed() < TIME_LIMIT_SEC) {
        ++trials;
        int i = (int)(rng() % n);
        int j = (int)(rng() % n);
        if (i == j) continue;
        int a = p[i], b = p[j];

        long long delta = 0;

        // Rows part
        for (int y = 0; y < n; ++y) {
            int ly = p[y];
            int ly_new = (y == i ? b : (y == j ? a : ly));
            int fiy = getF(i, y);
            int fjy = getF(j, y);
            if (fiy) delta += (long long)(getD(b, ly_new) - getD(a, ly));
            if (fjy) delta += (long long)(getD(a, ly_new) - getD(b, ly));
        }

        // Cols part
        for (int x = 0; x < n; ++x) {
            int lx = p[x];
            int lx_new = (x == i ? b : (x == j ? a : lx));
            int fxi = getF(x, i);
            int fxj = getF(x, j);
            if (fxi) delta += (long long)(getD(lx_new, b) - getD(lx, a));
            if (fxj) delta += (long long)(getD(lx_new, a) - getD(lx, b));
        }

        // Subtract pairs counted twice (both in rows and cols)
        int Fii = getF(i, i);
        int Fij = getF(i, j);
        int Fji = getF(j, i);
        int Fjj = getF(j, j);
        if (Fii) delta -= (long long)(getD(b, b) - getD(a, a));
        if (Fij) delta -= (long long)(getD(b, a) - getD(a, b));
        if (Fji) delta -= (long long)(getD(a, b) - getD(b, a));
        if (Fjj) delta -= (long long)(getD(a, a) - getD(b, b));

        if (delta < 0) {
            swap(p[i], p[j]);
            inv[a] = j;
            inv[b] = i;
        }
    }

    // Output permutation (1-indexed)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}