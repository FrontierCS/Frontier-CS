#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n, m;
    cin >> n >> m;
    const double eta = 0.1;
    vector<int> mistakes(n, 0);

    for (int t = 0; t < m; ++t) {
        string s;
        cin >> s;
        // Find minimum mistakes in each group
        int min0 = INT_MAX, min1 = INT_MAX;
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                if (mistakes[i] < min0) min0 = mistakes[i];
            } else {
                if (mistakes[i] < min1) min1 = mistakes[i];
            }
        }

        // Compute sums of exponential weights relative to the minimum in each group
        double sum0 = 0.0, sum1 = 0.0;
        if (min0 != INT_MAX) {
            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') {
                    int d = mistakes[i] - min0;
                    if (d * eta <= 700) {   // exp(-700) ~ 1e-304, safe for double
                        sum0 += exp(-eta * d);
                    }
                }
            }
        }
        if (min1 != INT_MAX) {
            for (int i = 0; i < n; ++i) {
                if (s[i] == '1') {
                    int d = mistakes[i] - min1;
                    if (d * eta <= 700) {
                        sum1 += exp(-eta * d);
                    }
                }
            }
        }

        // Compute logarithmic scores
        double score0 = (min0 == INT_MAX || sum0 == 0.0) ? -1e100 : (-eta * min0 + log(sum0));
        double score1 = (min1 == INT_MAX || sum1 == 0.0) ? -1e100 : (-eta * min1 + log(sum1));
        char prediction = (score0 >= score1) ? '0' : '1';
        cout << prediction << endl;

        char outcome;
        cin >> outcome;
        // Update mistake counts for experts that were wrong
        for (int i = 0; i < n; ++i) {
            if ((s[i] == '1') != (outcome == '1')) {
                mistakes[i]++;
            }
        }
    }

    return 0;
}