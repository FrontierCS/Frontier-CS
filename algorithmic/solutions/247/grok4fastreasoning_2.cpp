#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<int> A(N + 1), B(N + 1);
    long long sumA = 0, sumB = 0;
    for (int i = 1; i <= N; i++) {
        cin >> A[i];
        sumA += A[i];
    }
    for (int i = 1; i <= N; i++) {
        cin >> B[i];
        sumB += B[i];
    }
    if (sumA != sumB) {
        cout << "No" << endl;
        return 0;
    }
    vector<int> curr = A;
    vector<pair<int, int>> ops;
    const int MAX_STEPS = 100000;
    bool reached = false;
    for (int step = 0; step < MAX_STEPS; step++) {
        // check if equal
        bool eq = true;
        int err = 0;
        for (int k = 1; k <= N; k++) {
            int dif = abs(curr[k] - B[k]);
            err += dif;
            if (curr[k] != B[k]) eq = false;
        }
        if (eq) {
            reached = true;
            break;
        }
        // find best pair
        int best_dec = -1;
        int best_i = N + 1;
        int best_j = N + 1;
        for (int ii = 1; ii <= N; ii++) {
            for (int jj = ii + 1; jj <= N; jj++) {
                int old_ei = abs(curr[ii] - B[ii]);
                int old_ej = abs(curr[jj] - B[jj]);
                int new_ai = curr[jj] - 1;
                int new_aj = curr[ii] + 1;
                int new_ei = abs(new_ai - B[ii]);
                int new_ej = abs(new_aj - B[jj]);
                int delta_err = new_ei + new_ej - old_ei - old_ej;
                int new_err = err + delta_err;
                if (new_err < err) {
                    int dec = err - new_err;
                    bool better = (dec > best_dec) ||
                                  (dec == best_dec && (ii < best_i || (ii == best_i && jj < best_j)));
                    if (better) {
                        best_dec = dec;
                        best_i = ii;
                        best_j = jj;
                    }
                }
            }
        }
        if (best_dec == -1) {
            break;
        }
        // perform
        ops.emplace_back(best_i, best_j);
        int temp = curr[best_i];
        curr[best_i] = curr[best_j] - 1;
        curr[best_j] = temp + 1;
    }
    // check final
    bool eq = true;
    for (int k = 1; k <= N; k++) {
        if (curr[k] != B[k]) eq = false;
    }
    if (eq && reached) {
        cout << "Yes" << endl;
        cout << ops.size() << endl;
        for (auto p : ops) {
            cout << p.first << " " << p.second << endl;
        }
    } else {
        cout << "No" << endl;
    }
    return 0;
}