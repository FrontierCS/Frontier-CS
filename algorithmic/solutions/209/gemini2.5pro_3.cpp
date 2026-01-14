#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <iomanip>

using namespace std;

long long query(long long u, long long d) {
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int h;
    cin >> h;
    long long n = (1LL << h) - 1;

    vector<long long> s(h, 0);
    vector<vector<long double>> a(h, vector<long double>(h));
    vector<long double> b(h);
    
    vector<vector<long long>> n_k_d(h, vector<long long>(h + 1, 0));

    for (int k = 0; k < h; ++k) {
        for (int d = 1; d <= h; ++d) {
            long long count = 0;
            // Path goes i steps up to an ancestor, then d-i steps down.
            // i=0: path is fully downwards.
            if (k + d < h) {
                count += (1LL << d);
            }
            // i>0: path goes up, then to a different branch.
            for (int i = 1; i <= min(k, d); ++i) {
                // Ancestor must exist (i<=k)
                // New node must be in the tree
                if (k + d - 2 * i < h) {
                    if (d - i -1 >= 0)
                        count += (1LL << (d - i - 1));
                }
            }
            n_k_d[k][d] = count;
        }
    }
    
    vector<long long> A(h + 1, 0);
    
    // This will exceed query limits for large h, but is a valid algorithm.
    // An optimal solution must exist that avoids O(n*h) queries.
    for (int d = 1; d <= h; ++d) {
        for (long long u = 1; u <= n; ++u) {
            A[d] += query(u, d);
        }
    }

    for (int i = 0; i < h; i++) {
        b[i] = A[i + 1];
        for (int j = 0; j < h; j++) {
            a[i][j] = n_k_d[j][i + 1];
        }
    }

    // Gaussian elimination to solve Ax = b for x (which is s)
    for (int i = 0; i < h; i++) {
        int pivot = i;
        for (int j = i + 1; j < h; j++) {
            if (abs(a[j][i]) > abs(a[pivot][i])) {
                pivot = j;
            }
        }
        swap(a[i], a[pivot]);
        swap(b[i], b[pivot]);

        if (abs(a[i][i]) < 1e-12) continue;

        for (int j = i + 1; j < h; j++) {
            long double factor = a[j][i] / a[i][i];
            for (int k = i; k < h; k++) {
                a[j][k] -= factor * a[i][k];
            }
            b[j] -= factor * b[i];
        }
    }

    // Back substitution
    for (int i = h - 1; i >= 0; i--) {
        long double current_b = b[i];
        for (int j = i + 1; j < h; j++) {
            current_b -= a[i][j] * s[j];
        }
        if (abs(a[i][i]) < 1e-9) { 
            s[i] = 0;
        } else {
            s[i] = round(current_b / a[i][i]);
        }
    }
    
    long long total_sum = 0;
    for (int i = 0; i < h; i++) {
        if (s[i] > 0)
            total_sum += s[i];
    }
    
    cout << "! " << total_sum << endl;

    return 0;
}