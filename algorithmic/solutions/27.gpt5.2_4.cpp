#include <bits/stdc++.h>
using namespace std;

struct Choice {
    long long k = -1;
    int type = 0; // 0 FULL, 1 CS, 2 PP, 3 PLANE
    int p = 0;
};

static vector<int> primes;

static vector<int> genPrimes(int upTo) {
    vector<bool> isPrime(upTo + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; 1LL * i * i <= upTo; i++) if (isPrime[i])
        for (int j = i * i; j <= upTo; j += i) isPrime[j] = false;
    vector<int> ps;
    for (int i = 2; i <= upTo; i++) if (isPrime[i]) ps.push_back(i);
    return ps;
}

static long long planeCount(int a, int b, int p) {
    long long P = p;
    long long p2 = P * P;
    if (p2 > b) return -1;
    long long includedInf = 0;
    if (b > p2) includedInf = min<long long>(b - p2, P + 1);
    long long includedPoints = p2 + includedInf;

    long long Vlines = p2 + P + 1;
    long long baseLines = min<long long>(a, Vlines);

    long long slopedUsed = min<long long>(baseLines, p2);
    long long vertUsed = 0;
    if (baseLines > p2) vertUsed = min<long long>(P, baseLines - p2);
    bool infLineUsed = (baseLines == Vlines);

    long long finiteEdges = (slopedUsed + vertUsed) * P;

    long long fullSlopes = slopedUsed / P;
    long long rem = slopedUsed % P;
    long long numSlopeInf = min<long long>(includedInf, P);

    long long infEdgesSloped = P * min<long long>(fullSlopes, numSlopeInf) + ((fullSlopes < numSlopeInf) ? rem : 0);
    long long infEdgesVertical = (includedInf == P + 1) ? vertUsed : 0;
    long long infEdgesInfinityLine = infLineUsed ? includedInf : 0;

    long long baseEdges = finiteEdges + infEdgesSloped + infEdgesVertical + infEdgesInfinityLine;
    long long total = baseEdges + (b - includedPoints) + (a - baseLines);

    long long cap = 1LL * a * b;
    if (total > cap) total = cap;
    return total;
}

static Choice bestChoice(int a, int b) {
    Choice best;

    if (a == 1 || b == 1) {
        best.k = 1LL * a * b;
        best.type = 0;
        best.p = 0;
        return best;
    }

    // CS: one full column + singletons
    {
        long long k = 1LL * a + b - 1;
        best = {k, 1, 0};
    }

    // PP: distinct row pairs per column + singletons
    {
        long long pairs = 1LL * a * (a - 1) / 2;
        long long k = 1LL * b + min<long long>(b, pairs);
        if (k > best.k) best = {k, 2, 0};
    }

    // PLANE: projective plane over prime p
    for (int p : primes) {
        if (1LL * p * p > b) break;
        long long k = planeCount(a, b, p);
        if (k > best.k) best = {k, 3, p};
    }

    return best;
}

static vector<pair<int,int>> buildEdges(int a, int b, const Choice& ch) {
    vector<pair<int,int>> e;
    if (ch.k <= 0) return e;
    e.reserve((size_t)min<long long>(ch.k, 100000));

    if (ch.type == 0) { // FULL (only valid when a==1 or b==1)
        for (int i = 1; i <= a; i++)
            for (int j = 1; j <= b; j++)
                e.push_back({i, j});
        return e;
    }

    if (ch.type == 1) { // CS
        for (int i = 1; i <= a; i++) e.push_back({i, 1});
        for (int j = 2; j <= b; j++) e.push_back({1, j});
        return e;
    }

    if (ch.type == 2) { // PP
        int col = 1;
        bool done = false;
        for (int u = 1; u <= a && !done; u++) {
            for (int v = u + 1; v <= a; v++) {
                if (col > b) { done = true; break; }
                e.push_back({u, col});
                e.push_back({v, col});
                col++;
            }
        }
        for (int c = col; c <= b; c++) e.push_back({1, c});
        return e;
    }

    // PLANE
    int p = ch.p;
    long long P = p;
    long long p2 = P * P;
    long long includedInf = 0;
    if (b > p2) includedInf = min<long long>(b - p2, P + 1);
    long long includedPoints = p2 + includedInf;

    long long Vlines = p2 + P + 1;
    int baseLines = (int)min<long long>(a, Vlines);

    for (int i = 1; i <= baseLines; i++) {
        if (i <= (int)p2) {
            int idx = i - 1;
            int s = idx / p;      // slope
            int t = idx % p;      // intercept
            for (int x = 0; x < p; x++) {
                int y = ( (long long)s * x + t ) % p;
                int col = x * p + y + 1;
                e.push_back({i, col});
            }
            if (includedInf > s) {
                int colInf = (int)p2 + s + 1;
                if (colInf <= b) e.push_back({i, colInf});
            }
        } else if (i <= (int)p2 + p) {
            int c = i - (int)p2 - 1; // vertical x=c
            for (int y = 0; y < p; y++) {
                int col = c * p + y + 1;
                e.push_back({i, col});
            }
            if (includedInf == P + 1) {
                int colInf = (int)p2 + p + 1;
                if (colInf <= b) e.push_back({i, colInf});
            }
        } else {
            // infinity line
            for (int t = 0; t < (int)includedInf; t++) {
                int colInf;
                if (t < p) colInf = (int)p2 + t + 1;
                else colInf = (int)p2 + p + 1; // vertical infinity
                if (colInf <= b) e.push_back({i, colInf});
            }
        }
    }

    // extra columns: singleton in row 1
    for (int col = (int)includedPoints + 1; col <= b; col++) e.push_back({1, col});
    // extra rows: singleton in column 1
    for (int row = baseLines + 1; row <= a; row++) e.push_back({row, 1});

    return e;
}

static vector<pair<int,int>> solveOrientation(int a, int b) {
    Choice ch = bestChoice(a, b);
    return buildEdges(a, b, ch);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    primes = genPrimes(400);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    auto e1 = solveOrientation(n, m);
    auto e2 = solveOrientation(m, n);

    // transpose e2
    for (auto &pr : e2) swap(pr.first, pr.second);

    const auto& ans = (e2.size() > e1.size()) ? e2 : e1;

    cout << ans.size() << "\n";
    for (auto [r, c] : ans) {
        cout << r << " " << c << "\n";
    }
    return 0;
}