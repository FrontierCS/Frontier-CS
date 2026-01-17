#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <iomanip>
#include <algorithm>

using namespace std;

long long query(long long u, long long d) {
    if (d <= 0) return 0;
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

void answer(long long s) {
    cout << "! " << s << endl;
}

int h;
long long n;

vector<vector<long long>> memo_N;

void precompute_N_k_d(int max_d) {
    memo_N.assign(h, vector<long long>(max_d + 1, -1));
    for (int k = 0; k < h; ++k) {
        for (int d = 1; d <= max_d; ++d) {
            long long count = 0;
            // Ancestor
            if (k >= d) {
                count++;
            }
            // Descendants
            if (k + d < h) {
                count += (1LL << d);
            }
            // Other subtrees
            for (int i = 1; i <= k && i < d; ++i) {
                int ancestor_depth = k - i;
                int dist_from_ancestor = d - i;
                if (ancestor_depth + dist_from_ancestor < h) {
                     count += (1LL << (dist_from_ancestor - 1));
                }
            }
            memo_N[k][d] = count;
        }
    }
}

void gaussian_elimination(vector<vector<double>>& a, vector<double>& ans) {
    int n_rows = a.size();
    if (n_rows == 0) return;
    int n_cols = a[0].size();

    for (int i = 0; i < n_rows; ++i) {
        int pivot = i;
        for (int j = i + 1; j < n_rows; ++j) {
            if (abs(a[j][i]) > abs(a[pivot][i])) {
                pivot = j;
            }
        }
        swap(a[i], a[pivot]);

        double div = a[i][i];
        for (int j = i; j < n_cols; ++j) {
            a[i][j] /= div;
        }

        for (int j = 0; j < n_rows; ++j) {
            if (i != j) {
                double mult = a[j][i];
                for (int k = i; k < n_cols; ++k) {
                    a[j][k] -= mult * a[i][k];
                }
            }
        }
    }

    ans.resize(n_rows);
    for (int i = 0; i < n_rows; ++i) {
        ans[i] = a[i][n_rows];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> h;
    n = (1LL << h) - 1;

    int num_eqs = h;
    vector<int> dists;
    for (int d = 1; dists.size() < num_eqs; ++d) {
        dists.push_back(d);
    }
    
    precompute_N_k_d(dists.back());

    vector<vector<double>> M_T(num_eqs, vector<double>(num_eqs + 1, 0));
    for (int i = 0; i < num_eqs; ++i) { // equation for k = i
        for (int j = 0; j < num_eqs; ++j) { // coefficient for c_j (d=dists[j])
            M_T[i][j] = memo_N[i][dists[j]];
        }
        M_T[i][num_eqs] = 1.0;
    }

    vector<double> c;
    gaussian_elimination(M_T, c);

    long double total_sum_d = 0;
    
    for (long long u = 1; u <= n; ++u) {
        for (int i = 0; i < num_eqs; ++i) {
            if (abs(c[i]) > 1e-9) {
                total_sum_d += c[i] * query(u, dists[i]);
            }
        }
    }
    
    answer(round(total_sum_d));

    return 0;
}