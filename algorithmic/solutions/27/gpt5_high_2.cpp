#include <bits/stdc++.h>
using namespace std;

struct LineRec {
    uint8_t type; // 0 = sloped y = a*x + b, 1 = vertical x = c
    int a, b, c;
    int cnt;
};

static bool isPrime(int x) {
    if (x < 2) return false;
    if (x % 2 == 0) return x == 2;
    for (int d = 3; 1LL * d * d <= x; d += 2) {
        if (x % d == 0) return false;
    }
    return true;
}

static int nextPrimeAtLeast(int x) {
    if (x <= 2) return 2;
    int p = x;
    while (!isPrime(p)) ++p;
    return p;
}

static vector<int> computeThresholds(int p, long long M) {
    vector<int> t(p);
    for (int x = 0; x < p; ++x) {
        long long v = M - 1 - x;
        if (v < 0) t[x] = -1;
        else t[x] = (int)(v / p);
    }
    return t;
}

static vector<LineRec> generateLinesCounts(int p, const vector<int>& t) {
    int p2 = p * p;
    vector<LineRec> lines;
    lines.reserve(p2 + p);
    // Sloped lines: y = a*x + b (mod p)
    for (int a = 0; a < p; ++a) {
        for (int b = 0; b < p; ++b) {
            int cnt = 0;
            for (int x = 0; x < p; ++x) {
                int tx = t[x];
                if (tx >= 0) {
                    int y = (a * x + b) % p;
                    if (y <= tx) ++cnt;
                }
            }
            LineRec L;
            L.type = 0; L.a = a; L.b = b; L.c = 0; L.cnt = cnt;
            lines.push_back(L);
        }
    }
    // Vertical lines: x = c
    for (int c = 0; c < p; ++c) {
        int cnt = t[c] >= 0 ? t[c] + 1 : 0;
        LineRec L;
        L.type = 1; L.a = 0; L.b = 0; L.c = c; L.cnt = cnt;
        lines.push_back(L);
    }
    return lines;
}

struct OptionResult {
    long long k;
    bool rowsAreLines; // true: rows as lines over columns; false: columns as lines over rows
    int used; // number of rows (if rowsAreLines) or columns (else)
    int p;
    long long M; // M = columns count if rowsAreLines, else rows count
    vector<int> t;
    vector<LineRec> selected;
};

static OptionResult buildOptionRowsAsLines(int n, int m) {
    OptionResult res;
    res.rowsAreLines = true;
    int p = nextPrimeAtLeast((int)ceil(sqrt((double)m)));
    res.p = p;
    res.M = m;
    res.t = computeThresholds(p, m);
    vector<LineRec> lines = generateLinesCounts(p, res.t);
    sort(lines.begin(), lines.end(), [](const LineRec& A, const LineRec& B){
        if (A.cnt != B.cnt) return A.cnt > B.cnt;
        if (A.type != B.type) return A.type < B.type;
        if (A.type == 0) {
            if (A.a != B.a) return A.a < B.a;
            return A.b < B.b;
        } else {
            return A.c < B.c;
        }
    });
    int pos = 0;
    while (pos < (int)lines.size() && lines[pos].cnt > 0) ++pos;
    int r = min(n, pos);
    res.used = r;
    res.k = 0;
    res.selected.clear();
    res.selected.reserve(r);
    for (int i = 0; i < r; ++i) {
        res.selected.push_back(lines[i]);
        res.k += lines[i].cnt;
    }
    return res;
}

static OptionResult buildOptionColumnsAsLines(int n, int m) {
    OptionResult res;
    res.rowsAreLines = false;
    int p = nextPrimeAtLeast((int)ceil(sqrt((double)n)));
    res.p = p;
    res.M = n;
    res.t = computeThresholds(p, n);
    vector<LineRec> lines = generateLinesCounts(p, res.t);
    sort(lines.begin(), lines.end(), [](const LineRec& A, const LineRec& B){
        if (A.cnt != B.cnt) return A.cnt > B.cnt;
        if (A.type != B.type) return A.type < B.type;
        if (A.type == 0) {
            if (A.a != B.a) return A.a < B.a;
            return A.b < B.b;
        } else {
            return A.c < B.c;
        }
    });
    int pos = 0;
    while (pos < (int)lines.size() && lines[pos].cnt > 0) ++pos;
    int r = min(m, pos);
    res.used = r;
    res.k = 0;
    res.selected.clear();
    res.selected.reserve(r);
    for (int i = 0; i < r; ++i) {
        res.selected.push_back(lines[i]);
        res.k += lines[i].cnt;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Special cases: if one dimension is 1, we can take all cells
    if (n == 1) {
        cout << m << "\n";
        for (int j = 1; j <= m; ++j) cout << 1 << " " << j << "\n";
        return 0;
    }
    if (m == 1) {
        cout << n << "\n";
        for (int i = 1; i <= n; ++i) cout << i << " " << 1 << "\n";
        return 0;
    }

    OptionResult optA = buildOptionRowsAsLines(n, m);
    OptionResult optB = buildOptionColumnsAsLines(n, m);

    OptionResult best = (optA.k >= optB.k ? optA : optB);

    vector<pair<int,int>> ans;
    ans.reserve((size_t)best.k);

    int p = best.p;
    if (best.rowsAreLines) {
        // Rows are lines over columns
        // For each selected line, assign it to row r = idx + 1
        for (int idx = 0; idx < best.used; ++idx) {
            int r = idx + 1;
            const LineRec &L = best.selected[idx];
            if (L.type == 0) {
                int a = L.a, b = L.b;
                for (int x = 0; x < p; ++x) {
                    int tx = best.t[x];
                    if (tx < 0) continue;
                    int y = (a * x + b) % p;
                    if (y <= tx) {
                        int col = x + p * y;
                        if (col < m) ans.emplace_back(r, col + 1);
                    }
                }
            } else {
                int c = L.c;
                for (int y = 0; y < p; ++y) {
                    int col = c + p * y;
                    if (col < m) ans.emplace_back(r, col + 1);
                }
            }
        }
    } else {
        // Columns are lines over rows
        // For each selected line, assign it to column c = idx + 1
        for (int idx = 0; idx < best.used; ++idx) {
            int ccol = idx + 1;
            const LineRec &L = best.selected[idx];
            if (L.type == 0) {
                int a = L.a, b = L.b;
                for (int x = 0; x < p; ++x) {
                    int tx = best.t[x];
                    if (tx < 0) continue;
                    int y = (a * x + b) % p;
                    if (y <= tx) {
                        int row = x + p * y;
                        if (row < n) ans.emplace_back(row + 1, ccol);
                    }
                }
            } else {
                int c = L.c;
                for (int y = 0; y < p; ++y) {
                    int row = c + p * y;
                    if (row < n) ans.emplace_back(row + 1, ccol);
                }
            }
        }
    }

    cout << ans.size() << "\n";
    for (auto &pr : ans) {
        cout << pr.first << " " << pr.second << "\n";
    }

    return 0;
}