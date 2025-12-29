#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <utility>
using namespace std;

struct Line {
    int a; // for non-vertical: slope, for vertical: -1
    int b; // intercept or x=c
    int cnt;
};

void output_points(vector<pair<int,int>>& points, bool swapped) {
    if (swapped) {
        for (auto& p : points) {
            swap(p.first, p.second);
        }
    }
    cout << points.size() << "\n";
    for (const auto& p : points) {
        cout << p.first << " " << p.second << "\n";
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    bool swapped = false;
    if (n > m) {
        swap(n, m);
        swapped = true;
    }

    // small construction possible score
    long long total_pairs = (long long)n * (n-1) / 2;
    long long k_small;
    if (m >= total_pairs) {
        k_small = m + total_pairs;
    } else {
        k_small = 2 * m;
    }

    // find prime p such that p^2 >= m
    int s = (int)ceil(sqrt(m));
    int p = s;
    while (true) {
        bool is_prime = true;
        for (int i = 2; i * i <= p; ++i) {
            if (p % i == 0) {
                is_prime = false;
                break;
            }
        }
        if (is_prime) break;
        ++p;
    }

    if (k_small >= (long long)n * p) {
        // use small construction
        vector<pair<int,int>> points;
        if (m >= total_pairs) {
            int next_col = 1;
            for (int i = 1; i <= n; ++i) {
                for (int j = i+1; j <= n; ++j) {
                    points.emplace_back(i, next_col);
                    points.emplace_back(j, next_col);
                    ++next_col;
                }
            }
            for (int col = next_col; col <= m; ++col) {
                points.emplace_back(1, col);
            }
        } else {
            int col = 1;
            for (int i = 1; i <= n; ++i) {
                for (int j = i+1; j <= n; ++j) {
                    if (col > m) break;
                    points.emplace_back(i, col);
                    points.emplace_back(j, col);
                    ++col;
                }
                if (col > m) break;
            }
        }
        output_points(points, swapped);
        return 0;
    }

    // otherwise, compute line construction
    vector<Line> lines;
    // non-vertical lines: y = a*x + b  (mod p)
    for (int a = 0; a < p; ++a) {
        for (int b = 0; b < p; ++b) {
            int cnt = 0;
            for (int x = 0; x < p; ++x) {
                int y = (a * x + b) % p;
                long long col = (long long)x * p + y + 1;
                if (col <= m) ++cnt;
            }
            lines.push_back({a, b, cnt});
        }
    }
    // vertical lines: x = c
    for (int c = 0; c < p; ++c) {
        int cnt = 0;
        for (int y = 0; y < p; ++y) {
            long long col = (long long)c * p + y + 1;
            if (col <= m) ++cnt;
        }
        lines.push_back({-1, c, cnt});
    }

    // sort by count descending
    sort(lines.begin(), lines.end(), [](const Line& l1, const Line& l2) {
        return l1.cnt > l2.cnt;
    });

    int num_lines = min(n, (int)lines.size());
    vector<bool> used_col(m+1, false);
    vector<pair<int,int>> points;
    int points_from_lines = 0;
    int distinct_used = 0;

    for (int i = 0; i < num_lines; ++i) {
        int row = i+1;
        const Line& line = lines[i];
        if (line.a == -1) { // vertical line x = line.b
            int c = line.b;
            for (int y = 0; y < p; ++y) {
                long long col = (long long)c * p + y + 1;
                if (col <= m) {
                    int col_int = (int)col;
                    points.emplace_back(row, col_int);
                    ++points_from_lines;
                    if (!used_col[col_int]) {
                        used_col[col_int] = true;
                        ++distinct_used;
                    }
                }
            }
        } else {
            int a = line.a;
            int b = line.b;
            for (int x = 0; x < p; ++x) {
                int y = (a * x + b) % p;
                long long col = (long long)x * p + y + 1;
                if (col <= m) {
                    int col_int = (int)col;
                    points.emplace_back(row, col_int);
                    ++points_from_lines;
                    if (!used_col[col_int]) {
                        used_col[col_int] = true;
                        ++distinct_used;
                    }
                }
            }
        }
    }

    long long k_line = points_from_lines + (m - distinct_used);
    if (k_line > k_small) {
        // add all unused columns to row 1
        for (int col = 1; col <= m; ++col) {
            if (!used_col[col]) {
                points.emplace_back(1, col);
            }
        }
        output_points(points, swapped);
    } else {
        // fall back to small construction
        vector<pair<int,int>> points_small;
        if (m >= total_pairs) {
            int next_col = 1;
            for (int i = 1; i <= n; ++i) {
                for (int j = i+1; j <= n; ++j) {
                    points_small.emplace_back(i, next_col);
                    points_small.emplace_back(j, next_col);
                    ++next_col;
                }
            }
            for (int col = next_col; col <= m; ++col) {
                points_small.emplace_back(1, col);
            }
        } else {
            int col = 1;
            for (int i = 1; i <= n; ++i) {
                for (int j = i+1; j <= n; ++j) {
                    if (col > m) break;
                    points_small.emplace_back(i, col);
                    points_small.emplace_back(j, col);
                    ++col;
                }
                if (col > m) break;
            }
        }
        output_points(points_small, swapped);
    }

    return 0;
}