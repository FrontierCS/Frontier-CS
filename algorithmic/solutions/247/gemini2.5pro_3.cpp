#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <utility>

using namespace std;

bool is_possible(int n, const vector<long long>& a, const vector<long long>& b) {
    long long sum_a = 0;
    long long sum_b = 0;
    for (int i = 0; i < n; ++i) {
        sum_a += a[i];
        sum_b += b[i];
    }
    if (sum_a != sum_b) {
        return false;
    }

    long long current_prefix_sum_a = 0;
    long long current_prefix_sum_b = 0;
    for (int k = 0; k < n - 1; ++k) {
        current_prefix_sum_a += a[k];
        current_prefix_sum_b += b[k];
        if (current_prefix_sum_a > current_prefix_sum_b) {
            return false;
        }
    }

    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<long long> a(n), b(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    for (int i = 0; i < n; ++i) cin >> b[i];

    if (!is_possible(n, a, b)) {
        cout << "No" << endl;
        return 0;
    }

    cout << "Yes" << endl;

    vector<pair<int, int>> ops;
    vector<long long> current_a = a;

    while (current_a != b) {
        int best_i = -1, best_j = -1;
        int best_op_type = 5; // 1: best, 2: semi-good, 3: neutral, 4: fallback

        // Priority 1: "Good" moves
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                if (current_a[i] < b[i] && current_a[j] > b[j] && current_a[j] == current_a[i] + 2) {
                    best_op_type = 1;
                    best_i = i;
                    best_j = j;
                    goto found_op;
                }
                if (current_a[i] > b[i] && current_a[j] < b[j] && current_a[j] == current_a[i]) {
                    best_op_type = 1;
                    best_i = i;
                    best_j = j;
                    goto found_op;
                }
            }
        }
        
        // Priority 2: "Semi-good" moves
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                if ((current_a[i] < b[i] || current_a[j] > b[j]) && current_a[j] == current_a[i] + 2) {
                    if (2 < best_op_type) {
                        best_op_type = 2;
                        best_i = i;
                        best_j = j;
                    }
                }
                if ((current_a[i] > b[i] || current_a[j] < b[j]) && current_a[j] == current_a[i]) {
                     if (2 < best_op_type) {
                        best_op_type = 2;
                        best_i = i;
                        best_j = j;
                    }
                }
            }
        }
        if(best_op_type <= 2) goto found_op;

        // Priority 3: Any elementary op
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                if (current_a[j] == current_a[i] + 2 || current_a[j] == current_a[i]) {
                    if (3 < best_op_type) {
                        best_op_type = 3;
                        best_i = i;
                        best_j = j;
                    }
                }
            }
        }
        if(best_op_type <= 3) goto found_op;
        
        // Priority 4: Fallback, any productive move
        for(int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (current_a[i] < b[i] && current_a[j] > b[j] && current_a[j] > current_a[i] + 1) {
                    best_i = i; best_j = j; goto found_op;
                }
                 if (current_a[i] > b[i] && current_a[j] < b[j] && current_a[i] > current_a[j] - 1) {
                    best_i = i; best_j = j; goto found_op;
                }
            }
        }

        // Final fallback: any value-changing op
        for(int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (current_a[j] != current_a[i] + 1) {
                    best_i = i; best_j = j; goto found_op;
                }
            }
        }

    found_op:
        long long old_ai = current_a[best_i];
        long long old_aj = current_a[best_j];
        current_a[best_i] = old_aj - 1;
        current_a[best_j] = old_ai + 1;
        ops.push_back({best_i + 1, best_j + 1});
    }

    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.first << " " << op.second << endl;
    }

    return 0;
}