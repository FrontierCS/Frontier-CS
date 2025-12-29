#include <iostream>
#include <vector>
#include <cmath>
#include <unordered_set>
#include <algorithm>
#include <cstring>
#include <array>

using namespace std;

vector<int> primes;

void sieve(int limit) {
    vector<bool> is_prime(limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= limit; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (long long j = 1LL * i * i; j <= limit; j += i)
                is_prime[j] = false;
        }
    }
}

// Greedy algorithm for small grids
vector<pair<int, int>> greedy(int n, int m) {
    vector<unordered_set<int>> rowCols(n + 1);
    vector<unordered_set<int>> colRows(m + 1);
    vector<pair<int, int>> points;
    for (int r = 1; r <= n; ++r) {
        for (int c = 1; c <= m; ++c) {
            bool ok = true;
            for (int rp : colRows[c]) {
                const auto& set1 = rowCols[r];
                const auto& set2 = rowCols[rp];
                // iterate over the smaller set
                if (set1.size() > set2.size()) {
                    for (int col : set2) {
                        if (set1.count(col)) {
                            ok = false;
                            break;
                        }
                    }
                } else {
                    for (int col : set1) {
                        if (set2.count(col)) {
                            ok = false;
                            break;
                        }
                    }
                }
                if (!ok) break;
            }
            if (ok) {
                points.push_back({r, c});
                rowCols[r].insert(c);
                colRows[c].insert(r);
            }
        }
    }
    return points;
}

// Affine construction: rows as points, columns as lines
vector<pair<int, int>> affine_rows_points(int p) {
    vector<pair<int, int>> points;
    for (int a = 0; a < p; ++a) {
        for (int b = 0; b < p; ++b) {
            int row = a * p + b + 1;
            // vertical line x = a
            int col_vert = a + 1;
            points.push_back({row, col_vert});
            // non-vertical lines y = m*x + c
            for (int m = 0; m < p; ++m) {
                int c = (b - m * a) % p;
                if (c < 0) c += p;
                int col_nonvert = p + m * p + c + 1;
                points.push_back({row, col_nonvert});
            }
        }
    }
    return points;
}

// Affine construction: rows as lines, columns as points
vector<pair<int, int>> affine_rows_lines(int p) {
    vector<pair<int, int>> points;
    // vertical lines as rows
    for (int x = 0; x < p; ++x) {
        int row = x + 1;
        for (int b = 0; b < p; ++b) {
            int col = x * p + b + 1;
            points.push_back({row, col});
        }
    }
    // non-vertical lines as rows: y = m*x + c
    for (int m = 0; m < p; ++m) {
        for (int c = 0; c < p; ++c) {
            int row = p + m * p + c + 1;
            for (int a = 0; a < p; ++a) {
                int b = (m * a + c) % p;
                int col = a * p + b + 1;
                points.push_back({row, col});
            }
        }
    }
    return points;
}

// Projective plane construction for prime p
vector<pair<int, int>> projective(int p) {
    int N = p * p + p + 1;
    vector<array<int, 3>> points_list, lines_list;
    // generate points: (a,b,1), (c,1,0), (1,0,0)
    for (int a = 0; a < p; ++a) {
        for (int b = 0; b < p; ++b) {
            points_list.push_back({a, b, 1});
        }
    }
    for (int c = 0; c < p; ++c) {
        points_list.push_back({c, 1, 0});
    }
    points_list.push_back({1, 0, 0});
    // generate lines (same representation)
    for (int u = 0; u < p; ++u) {
        for (int v = 0; v < p; ++v) {
            lines_list.push_back({u, v, 1});
        }
    }
    for (int w = 0; w < p; ++w) {
        lines_list.push_back({w, 1, 0});
    }
    lines_list.push_back({1, 0, 0});

    vector<pair<int, int>> result;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int dot = lines_list[i][0] * points_list[j][0]
                    + lines_list[i][1] * points_list[j][1]
                    + lines_list[i][2] * points_list[j][2];
            if (dot % p == 0) {
                result.push_back({i + 1, j + 1});
            }
        }
    }
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    sieve(400); // primes up to 400

    int n, m;
    cin >> n >> m;

    // For very small grids, use greedy
    if (n * m <= 10000) {
        auto points = greedy(n, m);
        cout << points.size() << '\n';
        for (auto [r, c] : points) {
            cout << r << ' ' << c << '\n';
        }
        return 0;
    }

    // Otherwise, try constructions
    int best_k = max(n, m); // baseline
    int best_p = -1, best_mode = 3; // 0: affine rows as points, 1: affine rows as lines, 2: projective, 3: baseline
    int R0 = 0, C0 = 0; // rows and columns used by construction

    // baseline configuration
    if (n >= m) {
        R0 = n; C0 = 1;
    } else {
        R0 = 1; C0 = m;
    }

    for (int p : primes) {
        // Affine with rows as points
        if (1LL * p * p <= n && 1LL * p * p + p <= m) {
            long long k = 1LL * p * p * (p + 1);
            if (k > best_k) {
                best_k = k;
                best_p = p;
                best_mode = 0;
                R0 = p * p;
                C0 = p * p + p;
            }
        }
        // Affine with rows as lines
        if (1LL * p * p + p <= n && 1LL * p * p <= m) {
            long long k = 1LL * p * p * (p + 1);
            if (k > best_k) {
                best_k = k;
                best_p = p;
                best_mode = 1;
                R0 = p * p + p;
                C0 = p * p;
            }
        }
        // Projective
        int N = p * p + p + 1;
        if (N <= n && N <= m) {
            long long k = 1LL * (p + 1) * N;
            if (k > best_k) {
                best_k = k;
                best_p = p;
                best_mode = 2;
                R0 = N;
                C0 = N;
            }
        }
    }

    vector<pair<int, int>> points;
    if (best_mode == 0) {
        points = affine_rows_points(best_p);
    } else if (best_mode == 1) {
        points = affine_rows_lines(best_p);
    } else if (best_mode == 2) {
        points = projective(best_p);
    } else { // baseline
        if (n >= m) {
            for (int i = 1; i <= n; ++i) points.push_back({i, 1});
        } else {
            for (int j = 1; j <= m; ++j) points.push_back({1, j});
        }
    }

    // Add safe extra points
    int A = min(n - R0, m - C0);
    for (int i = 1; i <= A; ++i) {
        points.push_back({R0 + i, C0 + i});
    }
    int remaining_cols = m - C0 - A;
    int B = min(R0, remaining_cols);
    for (int i = 1; i <= B; ++i) {
        points.push_back({i, C0 + A + i});
    }

    cout << points.size() << '\n';
    for (auto [r, c] : points) {
        cout << r << ' ' << c << '\n';
    }

    return 0;
}