#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

// The problem limits n * m <= 100000.
// By ensuring n <= m, we guarantee n <= sqrt(100000) approx 316.
// We use a safe upper bound for the arrays.
const int MAXN = 350;

// used[i][j] indicates whether row i and row j have appeared together in the same column.
// If true, they cannot be placed together in any future column to avoid forming a rectangle.
bool used[MAXN][MAXN];

// deg[i] stores the number of other rows that row i is already paired with.
// This serves as a heuristic to prioritize rows that are less constrained.
int deg[MAXN];

struct Point {
    int r, c;
};

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return 0;

    // To optimize the greedy process, we work with the smaller dimension as rows.
    // If the input has more rows than columns, we swap them internally and swap back for output.
    bool swapped = false;
    int n = n_in;
    int m = m_in;
    if (n > m) {
        swap(n, m);
        swapped = true;
    }

    // Initialize random number generator with a fixed seed for reproducibility (and valid submission)
    mt19937 rng(42);

    // Vector containing row indices 0 to n-1
    vector<int> rows(n);
    for (int i = 0; i < n; ++i) rows[i] = i;

    vector<Point> result;
    // A rough upper bound for vector reservation could be helpful but not strictly necessary given limits.
    // result.reserve(n * m); 

    // Iterate through each column to decide which rows to place points in
    for (int col = 0; col < m; ++col) {
        // Shuffle rows to introduce randomness, helping to avoid getting stuck in local optima
        shuffle(rows.begin(), rows.end(), rng);

        // Sort rows based on their degree.
        // We prefer rows with lower degree (fewer existing constraints) to maximize placement chances.
        // stable_sort maintains the relative order of equivalent elements from the shuffle.
        stable_sort(rows.begin(), rows.end(), [&](int a, int b) {
            return deg[a] < deg[b];
        });

        vector<int> current_col_rows;
        // Greedily select rows that are compatible with all currently selected rows in this column
        for (int r : rows) {
            bool compatible = true;
            for (int existing_r : current_col_rows) {
                // Check if pair {r, existing_r} is already used
                if (used[r][existing_r]) {
                    compatible = false;
                    break;
                }
            }
            if (compatible) {
                current_col_rows.push_back(r);
            }
        }

        // Add the chosen points to the result and update the usage constraints
        for (size_t i = 0; i < current_col_rows.size(); ++i) {
            int u = current_col_rows[i];
            // Store result with 1-based indexing
            result.push_back({u + 1, col + 1});

            // Mark all pairs in this column as used
            for (size_t j = i + 1; j < current_col_rows.size(); ++j) {
                int v = current_col_rows[j];
                // Mark pair (u, v)
                // Note: checks are redundant here as the greedy step ensures !used[u][v]
                used[u][v] = true;
                used[v][u] = true;
                deg[u]++;
                deg[v]++;
            }
        }
    }

    // Output the total count of points
    cout << result.size() << "\n";
    
    // Output the coordinates of each point
    for (const auto& pt : result) {
        if (swapped) {
            // If we swapped dimensions, print (col, row)
            cout << pt.c << " " << pt.r << "\n";
        } else {
            // Otherwise print (row, col)
            cout << pt.r << " " << pt.c << "\n";
        }
    }

    return 0;
}